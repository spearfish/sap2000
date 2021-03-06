import win32com.client as win32
from sap2000.constants import UNITS
from sap2000.sap_groups import SapGroups
from sap2000.sap_areas import SapAreaObjects, SapAreaElements
from sap2000.sap_points import SapPointObjects, SapPointElements
from sap2000.sap_lines import SapLineElements
from sap2000.sap_frames import SapFrameObjects
from sap2000.sap_analysis import SapAnalysis


class Sap2000(object):
  def __init__(self):
    super(Sap2000, self).__init__()

    # create the Sap2000 COM-object
    sap_com_object = win32.Dispatch("SAP2000v15.sapobject")
    self.sap_com_object = sap_com_object

    # Each of the following attributes represents an object of the SAP2000 type 
    # library.
    # Each attribute is an instance of a subclass of SapBase.
    self.model = None
    self.groups = SapGroups(sap_com_object)
    self.area_elements = SapAreaElements(sap_com_object)
    self.point_elements = SapPointElements(sap_com_object)
    self.line_elements = SapLineElements(sap_com_object)
    self.area_objects = SapAreaObjects(sap_com_object)
    self.point_objects = SapPointObjects(sap_com_object)
    self.frame_objects = SapFrameObjects(sap_com_object)
    self.analysis = SapAnalysis(sap_com_object)

  def reset(self, units="kip_in_F",template = None):
    if self.model != None:
      self.model.File.Save()

    if template is None:
      self.model = self.initializeModel(units)
    else:
      self.open(template)
      self.model = self.sap_com_object.SapModel

  def start(self, units="kip_in_F", visible=True, filename=""):
    """
    Starts the Sap2000 application.

    When the model is not visible it does not appear on screen and it does
    not appear in the Windows task bar.  If no filename is specified, you
    can later open a model or create a model through the API.  The file name
    must have an .sdb, .$2k, .s2k, .xls, or .mdb extension. Files with .sdb
    extensions are opened as standard SAP2000 files. Files with .$2k and
    .s2k extensions are imported as text files. Files with .xls extensions
    are imported as Microsoft Excel files. Files with .mdb extensions are
    imported as Microsoft Access files.
    """
    units = UNITS[units]
    self.sap_com_object.ApplicationStart(units, visible, filename)
    self.model = self.sap_com_object.SapModel

  def exit(self, save_file=True):
    """ If the model file is saved then it is saved with its current name. """
    ret = self.sap_com_object.ApplicationExit(save_file)
    assert ret == 0
    self.sap_com_object = 0

    return 0

  def hide(self):
    """
    This function hides the Sap2000 application. When the application is
    hidden it is not visible on the screen or on the Windows task bar.  If
    the application is already hidden calling this function returns an
    error.
    """
    self.sap_com_object.Hide()

  def show(self):
    """
    This function unhides the Sap2000 application, that is, it makes it
    visible.  When the application is hidden, it is not visible on the
    screen or on the Windows task bar.  If the application is already
    visible (not hidden) calling this function returns an error.
    """
    self.sap_com_object.Unhide()

  def open(self, filename):
    """
    This function opens an existing Sap2000 file.

    The file name must have an sdb, $2k, s2k, xlsx, xls, or mdb extension.
    Files with sdb extensions are opened as standard Sap2000 files. Files
    with $2k and s2k extensions are imported as text files. Files with xlsx
    and xls extensions are imported as Microsoft Excel files. Files with mdb
    extensions are imported as Microsoft Access files.
    """
    return_value = self.sap_com_object.SapModel.File.OpenFile(filename)
    assert return_value == 0        # Ensure that everything went as expected

  def save(self, filename=""):
    """
    If a file name is specified, it should have an .sdb extension. If no file 
    name is specified the file is saved using its current name. If there is no 
    current name for the file (the file has not been saved previously) and this 
    function is called with no file name specified, an error will be returned.
    """
    return_value = self.sap_com_object.SapModel.File.Save(filename)
    assert return_value == 0        # Ensure that everything went as expected

  def initializeModel(self, units = "kip_in_F"):
    """
    This functions initializes a new SapModel and returns a way to directly 
    access it
    """
    model = self.sap_com_object.SapModel
    units = UNITS[units]
    return_value = model.InitializeNewModel(units)
    assert return_value == 0        # Ensure everything went as expected

    self.model = model    # Keep track of model

    return model

  def refreshview(self, window = 0, zoom = True):
    '''
    This functions updates the display so it is much faster
    than refreshwindows())
    '''
    return_value = self.sap_com_object.SapModel.View.RefreshView(window, zoom)

  def refreshwindow(self,window = 0):
    '''
    This functions updates the Program Windows. Should be used after adding,
    removing, or significantly modifying a new object/element in the model.
    '''
    return_value = self.sap_com_object.SapModel.View.RefreshWindow(window)