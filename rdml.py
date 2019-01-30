#!/usr/bin/python

import sys
import os
import re
import datetime
import zipfile
import argparse
from lxml import etree as ET


class RdmlError(Exception):
    """Basic exception for errors raised by the RDML-Python library"""
    def __init__(self, message):
        Exception.__init__(self, message)
    pass


class secondError(RdmlError):
    """Just to have, not used yet"""
    def __init__(self, message):
        RdmlError.__init__(self, message)
    pass


def _getFirstChild(base, id):
    """Returns the first child element with a defined id"""
    for node in base:
        if node.tag == "{http://www.rdml.org}" + id:
            return node
    return None


def _getFirstChildText(base, id):
    """Returns the first child element with a defined id text"""
    for node in base:
        if node.tag == "{http://www.rdml.org}" + id:
            return node.text
    return ""


def _addFirstChildToDic(base, dic, opt, id):
    """Adds the first child element with a defined id text to the dic"""
    for node in base:
        if node.tag == "{http://www.rdml.org}" + id:
            dic[id] = node.text
            return dic
    if not opt:
        dic[id] = ""
    return dic


def _getAllChilds(base, id):
    """Returns a list of all child elements with a defined id"""
    ret = []
    for node in base:
        if node.tag == "{http://www.rdml.org}" + id:
            ret.append(node)
    return ret


class Rdml:
    """RDML-Python library
    
    The root element used to open, write, read and edit RDML files.
    
    Attributes:
        _rdmlData: The RDML XML object from lxml.
        _node: The root node of the RDML XML object.
        _rdmlVersion: A string like '1.2' with the version of the rdmlData object.
    """

    def __init__(self, filename=None):
        """Inits an empty RDML instance with new() or load RDML file with load().

        Args:
            self: The class self parameter.
            filename: The name of the RDML file to load.

        Returns:
            No return value. Function may raise RdmlError if required.
        """
        
        self._rdmlData = None
        self._node = None
        self._rdmlVersion = '0.0'
        if filename:
            self.load(filename)
        else:
            self.new()

    def new(self):
        """Creates an new empty RDML object with the current date.

        Args:
            self: The class self parameter.

        Returns:
            No return value. Function may raise RdmlError if required.
        """

        data = "<rdml version='1.2' xmlns:rdml='http://www.rdml.org' xmlns='http://www.rdml.org'>\n<dateMade>"
        data += datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S")
        data += "</dateMade>\n</rdml>"
        self.loadXMLString(data)
        return

    def load(self, filename):
        """Load an RDML file with decompression of rdml_data.xml or an XML file. Uses loadXMLString().

        Args:
            self: The class self parameter.
            filename: The name of the RDML file to load.

        Returns:
            No return value. Function may raise RdmlError if required.
        """    

        if zipfile.is_zipfile(filename):
            zf = zipfile.ZipFile(filename, 'r')
            try:
                data = zf.read('rdml_data.xml').decode('utf-8')
            except KeyError:
                raise RdmlError('No rdml_data.xml in compressed RDML file found.')
            else:
                self.loadXMLString(data)
        else:
            with open(filename, 'r') as txtfile:
                data = txtfile.read()
                if data:
                    self.loadXMLString(data)
                else:
                    raise RdmlError('File format error, not a valid RDML or XML file.')

    def save(self, filename):
        """Save an RDML file with compression of rdml_data.xml.

        Args:
            self: The class self parameter.
            filename: The name of the RDML file to save to.

        Returns:
            No return value. Function may raise RdmlError if required.
        """

        data = ET.tostring(self._rdmlData, pretty_print=True)
        zf2 = zipfile.ZipFile(filename, mode='w', compression=zipfile.ZIP_DEFLATED,)
        try:
            zf2.writestr('rdml_data.xml', data)
        finally:
            zf2.close()

    def loadXMLString(self, data):
        """Create RDML object from xml string. !ENTITY and DOCSTRINGS will be removed.

        Args:
            self: The class self parameter.
            data: The xml string of the RDML file to load.

        Returns:
            No return value. Function may raise RdmlError if required.
        """

        # To avoid some xml attacs based on
        # <!ENTITY entityname "replacement text">
        data = re.sub(r"<\W*!ENTITY[^>]+>", "", data)
        data = re.sub(r"!ENTITY", "", data)
        try:
            self._rdmlData = ET.ElementTree(ET.fromstring(data))
        except ET.XMLSyntaxError:
            raise RdmlError('XML load error, not a valid RDML or XML file.')
        self._node = self._rdmlData.getroot()
        if self._node.tag != '{http://www.rdml.org}rdml':
            raise RdmlError('Root element is not \'rdml\', not a valid RDML or XML file.')
        self._rdmlVersion = self._node.get('version')
        # Remainder: Update version in new() and validate()
        if not self._rdmlVersion in ['1.0','1.1','1.2']:
            raise RdmlError('Unknown or unsupported RDML file version.')

    def validate(self, filename=None):
        """Validate the RDML object against its schema or load file and validate it.

        Args:
            self: The class self parameter.
            filename: The name of the RDML file to load.

        Returns:
            A string with the validation result as a two column table.
        """

        notes = ""
        if filename:
            try:
                vd = Rdml(filename)
            except RdmlError as err:
                notes += 'RDML file structure:\tFalse\t' + str(err) + '\n'
                return notes
            notes += "RDML file structure:\tTrue\tValid file structure.\n"
        else:
            vd = self
        version = vd.version()
        rdmlws = os.path.dirname(os.path.abspath(__file__))
        if version == '1.0':
            xmlschema_doc = ET.parse(os.path.join(rdmlws, 'schema', 'RDML_v1_0_REC.xsd'))
        elif version == '1.1':
            xmlschema_doc = ET.parse(os.path.join(rdmlws, 'schema', 'RDML_v1_1_REC.xsd'))
        elif version == '1.2':
            xmlschema_doc = ET.parse(os.path.join(rdmlws, 'schema', 'RDML_v1_2_REC.xsd'))
        else:
            notes += 'RDML version:\tFalse\tUnknown schema version' + version + '\n'
            return notes
        notes += "RDML version:\tTrue\t" + version + "\n"

        xmlschema = ET.XMLSchema(xmlschema_doc)
        result = xmlschema.validate(vd._rdmlData)
        if result:
            notes += 'Schema validation result:\tTrue\tRDML file is valid.\n'
        else:
            notes += 'Schema validation result:\tFalse\tRDML file is not valid.\n'
        log = xmlschema.error_log
        for err in log:
            notes += 'Schema validation error:\tFalse\t'
            notes += "Line %s, Column %s: %s \n" % (err.line, err.column, err.message)
        return notes

    def isvalid(self, filename=None):
        """Validate the RDML object against its schema or load file and validate it.

        Args:
            self: The class self parameter.
            filename: The name of the RDML file to load.

        Returns:
            True or false as the validation result.
        """

        if filename:
            try:
                vd = Rdml(filename)
            except RdmlError as err:
                return False
        else:
            vd = self
        version = vd.version()
        rdmlws = os.path.dirname(os.path.abspath(__file__))
        if version == '1.0':
            xmlschema_doc = ET.parse(os.path.join(rdmlws, 'schema', 'RDML_v1_0_REC.xsd'))
        elif version == '1.1':
            xmlschema_doc = ET.parse(os.path.join(rdmlws, 'schema', 'RDML_v1_1_REC.xsd'))
        elif version == '1.2':
            xmlschema_doc = ET.parse(os.path.join(rdmlws, 'schema', 'RDML_v1_2_REC.xsd'))
        else:
            return False
        xmlschema = ET.XMLSchema(xmlschema_doc)
        result = xmlschema.validate(vd._rdmlData)
        if result:
            return True
        else:
            return False

    def version(self):
        """Returns the version string of the RDML object.

        Args:
            self: The class self parameter.

        Returns:
            A string of the version like '1.1'.
        """

        return self._rdmlVersion

    def experimenters(self):
        exp = _getAllChilds(self._node, "experimenter")
        ret = []
        for node in exp:
            ret.append(Experimenter(node, self._rdmlVersion))
        return ret

    def tojson(self):
        """Returns a json of the RDML object without fluorescence data.

        Args:
            self: The class self parameter.

        Returns:
            A json of the data.
        """

        allExperimenters = self.experimenters()
        experimenters = []
        for exp in allExperimenters:
            experimenters.append(exp.tojson())

        data = {
            "rdml": {
                "version": self.version(),
                "dateMade": _getFirstChildText(self._node, "dateMade"),
                "dateUpdated": _getFirstChildText(self._node, "dateUpdated"),
                "experimenters": experimenters
            }
        }
        return data


class Experimenter:
    """RDML-Python library

    The experimenter element used to read and edit one experimenter.

    Attributes:
        _node: The experimenter node of the RDML XML object.
        _rdmlVersion: A string like '1.2' with the version of the rdmlData object.
    """

    def __init__(self, node, version):
        """Inits an empty RDML instance with new() or load RDML file with load().

        Args:
            self: The class self parameter.
            node: The experimenter node.

        Returns:
            No return value. Function may raise RdmlError if required.
        """

        self._node = node
        self._rdmlVersion = version

    def __getitem__(self, key):
        """Returns a json of the RDML object without fluorescence data.

        Args:
            self: The class self parameter.
            key: The key of the experimenter subelement

        Returns:
            A string of the data or None.
        """
        if key == "id":
            return self._node.get('id')

        if key in ["firstName", "lastName"]:
            return _getFirstChildText(self._node, key)

        if key in ["email", "labName", "labAddress"]:
            var = _getFirstChildText(self._node, key)
            if var == "":
                return None
            else:
                return var

        raise KeyError

    def tojson(self):
        """Returns a json of the RDML object without fluorescence data.

        Args:
            self: The class self parameter.

        Returns:
            A json of the data.
        """

        data = {
            "id": self._node.get('id'),
            "firstName": _getFirstChildText(self._node, "firstName"),
            "lastName": _getFirstChildText(self._node, "lastName")
        }
        _addFirstChildToDic(self._node, data, True, "email")
        _addFirstChildToDic(self._node, data, True, "labName")
        _addFirstChildToDic(self._node, data, True, "labAddress")
        return data


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='The command line interface to the RDML-Python library.')
    parser.add_argument('-v', '--validate', metavar="data.rdml", dest='validate', help='validate file against schema')
    parser.add_argument("-d", "--doooo", dest="doooo", help="just do stuff")

    args = parser.parse_args()

    # Validate RDML file
    if args.validate:
        inst = Rdml()
        res = inst.validate(filename=args.validate)
        print(res)
        sys.exit(0)

    # Tryout things
    if args.doooo:
        print('Tryout')
        xx = Rdml('rdml_data.xml')
        xx.getRoot()
        xx.save('new.rdml')

# if __name__ == '__main__':
 #   xx = Rdml()
#    xx.load('example.rdml')
  #  xx.load('err_doub.rdml')
#    print (dir(zipfile))
#    print zipfile.builtin_module_names
  #  try:
    #    xx.getRoot()
   #     xx.validate()
  #      xx.version()
 #   except RdmlError as e:
#  print(e)
