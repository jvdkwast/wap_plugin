# -*- coding: utf-8 -*-
"""
/***************************************************************************
 WAPlugin
                                 A QGIS plugin
 Provides access to all the WaPOR data and includes it in the QGIS canvas as another raster layer, providing WaPOR data easy access to the QGIS users. Moreover, the water accounting and productivity component of the plugin will help the water management, providing the opportunity of calculating water accounting indicators, through the creation of maps and reports.
 Generated by Plugin Builder: http://g-sherman.github.io/Qgis-Plugin-Builder/
                              -------------------
        begin                : 2020-12-01
        git sha              : $Format:%H$
        copyright            : (C) 2020 by WAP Team
        email                : waporteam17@gmail.com
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""
from qgis.PyQt.QtCore import QSettings, QTranslator, QCoreApplication, QDate, QTime, QDateTime, Qt
from qgis.PyQt.QtGui import QIcon 
from qgis.PyQt.QtWidgets import QAction, QApplication

from qgis.analysis import QgsRasterCalculatorEntry, QgsRasterCalculator
from qgis.core import QgsRasterLayer

# Initialize Qt resources from file resources.py
from .resources import *
# Import the code for the dialog
from .wap_plugin_dialog import WAPluginDialog
import os.path

from .managers import WaporAPIManager, FileManager, CanvasManager
from .indicators import IndicatorCalculator, INDICATORS_LIST, INDICATORS_INFO
from .tools import CoordinatesSelectorTool

# from PyQt5.QtGui import *
import requests
import json
import wget
import os  

class WAPlugin:
    """QGIS Plugin Implementation."""

    def __init__(self, iface):
        """Constructor.

        :param iface: An interface instance that will be passed to this class
            which provides the hook by which you can manipulate the QGIS
            application at run time.
        :type iface: QgsInterface
        """
        
        # Save reference to the QGIS interface
        self.iface = iface
        # initialize plugin directory
        self.plugin_dir = os.path.dirname(__file__)

        # initialize locale
        locale = QSettings().value('locale/userLocale')[0:2]
        locale_path = os.path.join(
            self.plugin_dir,
            'i18n',
            'WAPlugin_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)
            QCoreApplication.installTranslator(self.translator)

        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'&WAPlugin')

        # Check if plugin was started the first time in current QGIS session
        # Must be set in initGui() to survive plugin reloads
        self.first_start = None

        # Path of the code Directory
        self.cwd = os.path.dirname(os.path.realpath(__file__))
        self.layer_folder_dir = os.path.join(self.cwd, "layers")

        # Default Values
        self.waterProductivityVar = "GBWP"
        self.resolutionVar = "100m"  #"250m" or "100m" , maybe "30m" works for some area
        self.startSeasonVar = "2015-01"  # "YYYY-DK" (Dekad)
        self.endSeasonVar = "2015-18"  # "YYYY-DK" (Dekad)
        self.indicator_index = 0
        self.indicator = "Equity"

        # Locations
        self.locListContinental = ["Algeria","Angola","Benin","Botswana","Burkina Faso","Burundi","Cameroon","Canary Islands"
            ,"Cape Verde","Central African Republic","Ceuta","Chad","Comoros","Côte d'Ivoire"
            ,"Democratic Republic of the Congo","Djibouti","Egypt","Equatorial Guinea","Eritrea","Ethiopia"
            ,"Gabon","Gambia","Ghana","Guinea","Guinea-Bissau","Kenya","Lesotho","Liberia","Libya"
            ,"Madagascar","Madeira","Malawi","Mali","Mauritania","Mauritius","Mayotte","Melilla"
            ,"Morocco"  ,"Mozambique","Namibia","Niger","Nigeria"  ,"Republic of the Congo"
            ,"Réunion","Rwanda","Saint Helena","São Tomé and Príncipe","Senegal","Seychelles"
            ,"Sierra Leone","Somalia","South Africa","Sudan","Swaziland","Tanzania","Togo","Tunisia"
            ,"Uganda","Western Sahara","Zambia","Zimbabwe"]

        self.locListNational = ["Benin","Burundi","Egypt","Ghana","Iraq","Jordan","Kenya","Lebanon","Mali","Morocco"
            ,"Mozambique","Niger","Palestine","Rwanda","South Sudan","Sudan","Syrian Arab Republic"
            ,"Tunisia","Uganda","Yemen"]

        self.locListSubNational = ["Awash, Ethiopia", "Bekaa, Lebanon", "Busia, Kenya", "Gezira, Sudan", "Koga, Ethiopia",
                "Lamego, Mozambique", "Office du Niger, Mali", "Zankalon, Egypt"] 

        # MODIFICATIONS AFTER OOP
        self.rasters_path = "layers"

        self.api_manag = WaporAPIManager()
        self.file_manag = FileManager(self.plugin_dir, self.rasters_path)
        self.canv_manag = CanvasManager(self.iface, self.plugin_dir, self.rasters_path)
        
        self.indic_calc = IndicatorCalculator(self.plugin_dir, self.rasters_path)



    # noinspection PyMethodMayBeStatic
    def tr(self, message):
        """Get the translation for a string using Qt translation API.

        We implement this ourselves since we do not inherit QObject.

        :param message: String for translation.
        :type message: str, QString

        :returns: Translated version of message.
        :rtype: QString
        """
        # noinspection PyTypeChecker,PyArgumentList,PyCallByClass
        return QCoreApplication.translate('WAPlugin', message)

    def add_action(
        self,
        icon_path,
        text,
        callback,
        enabled_flag=True,
        add_to_menu=True,
        add_to_toolbar=True,
        status_tip=None,
        whats_this=None,
        parent=None):
        """Add a toolbar icon to the toolbar.

        :param icon_path: Path to the icon for this action. Can be a resource
            path (e.g. ':/plugins/foo/bar.png') or a normal file system path.
        :type icon_path: str

        :param text: Text that should be shown in menu items for this action.
        :type text: str

        :param callback: Function to be called when the action is triggered.
        :type callback: function

        :param enabled_flag: A flag indicating if the action should be enabled
            by default. Defaults to True.
        :type enabled_flag: bool

        :param add_to_menu: Flag indicating whether the action should also
            be added to the menu. Defaults to True.
        :type add_to_menu: bool

        :param add_to_toolbar: Flag indicating whether the action should also
            be added to the toolbar. Defaults to True.
        :type add_to_toolbar: bool

        :param status_tip: Optional text to show in a popup when mouse pointer
            hovers over the action.
        :type status_tip: str

        :param parent: Parent widget for the new action. Defaults None.
        :type parent: QWidget

        :param whats_this: Optional text to show in the status bar when the
            mouse pointer hovers over the action.

        :returns: The action that was created. Note that the action is also
            added to self.actions list.
        :rtype: QAction
        """

        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)

        if status_tip is not None:
            action.setStatusTip(status_tip)

        if whats_this is not None:
            action.setWhatsThis(whats_this)

        if add_to_toolbar:
            # Adds plugin icon to Plugins toolbar
            self.iface.addToolBarIcon(action)

        if add_to_menu:
            self.iface.addPluginToMenu(
                self.menu,
                action)

        self.actions.append(action)

        return action

    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""

        icon_path = ':/plugins/wap_plugin/icon.png'
        self.add_action(
            icon_path,
            text=self.tr(u'Water Accounting and Productivity Plugin'),
            callback=self.run,
            parent=self.iface.mainWindow())

        # will be set False in run()
        self.first_start = True


    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginMenu(
                self.tr(u'&WAPlugin'),
                action)
            self.iface.removeToolBarIcon(action)

    def signin(self):
        self.dlg.signinStateLabel.setText('Signing into your WaPOR profile . . .')
        connected = self.api_manag.signin(self.dlg.apiTokenTextBox.text())

        if connected:
            self.dlg.signinStateLabel.setText('API Token confirmed, access granted!!!')
            self.dlg.saveTokenButton.setEnabled(True)
            self.dlg.signinButton.setEnabled(False)

            self.dlg.progressBar.setValue(20)
            self.dlg.downloadButton.setEnabled(True)
            self.dlg.progressLabel.setText ('Connected to WaPOR database')
        else:
            self.dlg.signinStateLabel.setText('Access denied, please check the API Token provided or the internet connection . . .')
            self.dlg.progressLabel.setText ('Fail to connect to Wapor Database . . .')

    def saveToken(self):
        self.file_manag.save_token(self.dlg.apiTokenTextBox.text())
        self.dlg.signinStateLabel.setText('Token file saved in memory . . .')

    def loadToken(self):
        APIToken = self.file_manag.load_token()

        if APIToken is not None:
            self.dlg.signinStateLabel.setText('Loading Token from memory and signing into your WaPOR profile . . .')
            connected = self.api_manag.signin(APIToken)

            if connected:
                self.dlg.signinStateLabel.setText('API Token confirmed, access granted!!!')
                self.dlg.signinButton.setEnabled(False)

                self.dlg.progressBar.setValue(20)
                self.dlg.downloadButton.setEnabled(True)
                self.dlg.progressLabel.setText ('Connected to WaPOR database')
            else:
                self.dlg.signinStateLabel.setText('Access denied, please check the API Token file or the internet connection . . .')
                self.dlg.progressLabel.setText ('Fail to connect to Wapor Database . . .')
        else:
            self.dlg.signinStateLabel.setText('No token file found in memory . . .')

    def listWorkspaces(self):
        self.dlg.workspaceComboBox.clear()
        workspaces = self.api_manag.pull_workspaces()
        self.dlg.workspaceComboBox.addItems(workspaces.values())

        index = self.dlg.workspaceComboBox.findText('WAPOR_2', QtCore.Qt.MatchFixedString)
        if index >= 0:
            self.dlg.workspaceComboBox.setCurrentIndex(index)

    def listRasterMemory(self):
        self.tif_files = self.file_manag.list_rasters(self.rasters_path)
        self.dlg.rasterMemoryComboBox.clear()
        self.dlg.rasterMemoryComboBox.addItems(self.tif_files.keys())

        self.dlg.TbpRasterComboBox.clear()
        self.dlg.TbpRasterComboBox.addItems(self.tif_files.keys())

        self.dlg.AetiRasterComboBox.clear()
        self.dlg.AetiRasterComboBox.addItems(self.tif_files.keys())

    def workspaceChange(self):
        self.dlg.progressLabel.setText ('Loading available cubes . . .')
        QApplication.processEvents()
        self.workspace = self.dlg.workspaceComboBox.currentText()
        self.cubes = self.api_manag.pull_cubes(self.workspace)

        listCubes = [cube for cube in self.cubes.keys() if 'clipped' not in cube]

        self.dlg.cubeComboBox.clear()
        self.dlg.cubeComboBox.addItems(listCubes)
        self.dlg.progressLabel.setText ('Cubes available ready!')

    def indicatorChange(self):
        self.indicator_key = self.dlg.indicatorListComboBox.currentText()
        self.dlg.indicInfoLabel.setText(INDICATORS_INFO[self.indicator_key]['info'])

    def cubeChange(self):
        try:
            self.dlg.progressLabel.setText ('Loading available dimensions and measures . . .')
            QApplication.processEvents()
            self.cube = self.cubes[self.dlg.cubeComboBox.currentText()]
            self.dimensions = self.api_manag.pull_cube_dims(self.workspace,self.cube)
            self.measures = self.api_manag.pull_cube_meas(self.workspace,self.cube)

            self.dlg.measureComboBox.clear()
            self.dlg.measureComboBox.addItems(self.measures.keys())
            self.dlg.dimensionComboBox.clear()
            self.dlg.dimensionComboBox.addItems(self.dimensions.keys())
            self.dlg.progressLabel.setText ('Dimensions and measures available ready!')

            self.dlg.outputRasterCubeID.setText('_'+self.cube+'.tif')
        except (KeyError) as exception:
            pass

    def measureChange(self):
        try:
            self.measure = self.measures[self.dlg.measureComboBox.currentText()]
        except (KeyError) as exception:
            pass

    def memberChange(self):
        try:
            self.member = self.members[self.dlg.memberComboBox.currentText()]
        except (KeyError) as exception:
            pass

    def dimensionChange(self):
        try:
            self.dlg.progressLabel.setText('Loading available members . . .')
            QApplication.processEvents()
            self.dimension = self.dimensions[self.dlg.dimensionComboBox.currentText()]
            self.members = self.api_manag.pull_cube_dim_membs(self.workspace,self.cube,self.dimension)

            self.dlg.memberComboBox.clear()
            self.dlg.memberComboBox.addItems(self.members.keys())
            self.dlg.progressLabel.setText ('Members available ready!')
        except (KeyError) as exception:
                    pass
    
    def downloadCropedRaster(self):
        params = dict()
        params['outputFileName'] = self.dlg.outputRasterName.text()+'_'+self.cube+'.tif'
        params['cube_code'] = self.cube
        params['cube_workspaceCode'] = self.workspace
        params['measures'] = [self.measure]
        params['dimensions'] = [{
                                    "code": self.dimension,
                                    "values": [self.member]
                                }]
        params['coordinates'] = [self.queryCoordinates]

        rast_url = self.api_manag.query_crop_raster(params)

        self.file_manag.download_raster(rast_url)
        
        self.listRasterMemory()

    def onStartDateChanged(self, qDate):
        # print('{0}/{1}/{2}'.format(qDate.day(), qDate.month(), qDate.year()))
        self.startSeasonVar = str(qDate.year()) + "-" + str(qDate.day())
        print("Set Start Date: ", self.startSeasonVar)

    def onEndDateChanged(self, qDate):
        # print('{0}/{1}/{2}'.format(qDate.day(), qDate.month(), qDate.year()))
        self.endSeasonVar = str(qDate.year()) + "-" + str(qDate.day())
        print("Set End Date: ", self.endSeasonVar)

    def loadRaster(self):
        raster_name = self.dlg.rasterMemoryComboBox.currentText()
        self.canv_manag.add_rast(raster_name)

    def refreshRasters(self):
        indic_dir = os.path.join(self.layer_folder_dir, "indic")
        self.raster1 = []
        self.raster1_dir = []
        for _, _, files in os.walk(indic_dir):
            for name in files:
                self.raster1_dir.append(os.path.join(indic_dir, name))
            self.raster1 = list(files)
        self.raster2 = self.raster1
        self.raster2_dir = self.raster1_dir

        self.dlg.raster1.clear()
        self.dlg.raster2.clear()

        self.dlg.raster1.addItems(self.raster1)
        self.dlg.raster2.addItems(self.raster2)

    def selectCoordinatesTool(self):
        self.dlg.getEdgesButton.setEnabled(False)
        self.dlg.resetToolButton.setEnabled(True)
        self.prev_tool = self.iface.mapCanvas().mapTool()
        self.coord_selc_tool.activate()
        self.iface.mapCanvas().setMapTool(self.coord_selc_tool)
    
    def savePolygon(self):
        self.dlg.savePolygonButton.setEnabled(False)
        self.queryCoordinates = self.coord_selc_tool.getCoordinatesBuffer()
        print(self.queryCoordinates)
        self.coord_selc_tool.deactivate()
        self.iface.mapCanvas().setMapTool(self.prev_tool)
        if self.queryCoordinates:
            self.dlg.TestCanvasLabel.setText ('The polygon selected has {} edges'.format(len(self.queryCoordinates)))
        else:
            self.dlg.TestCanvasLabel.setText ('Polygon not valid.')

    def resetTool(self):
        """ 
        1. Get Edges
        2. Save Polygon
        3. Reset

        Initially:
            2 and 3 are disabled
        When 1 is clicked,
        Once 1 is clicked, its disabled too. And 3 is enabled.
        2 will be enabled only after getting three points. 

        When 2 is clicked, 1 and 2 are disabled and 3 is enabled. 

        When 3 is clicked, remove polygon and clear edges and 1 is enabled

        Show Number of Edges selected. Info """
        self.queryCoordinates = None
        self.dlg.TestCanvasLabel.setText ('Coordinates cleared, using default ones . . .')
        self.dlg.getEdgesButton.setEnabled(True)
        self.dlg.resetToolButton.setEnabled(False)

    def calculateIndex(self):
        print('Calculating . . . ')
        
        tbp_name = self.dlg.TbpRasterComboBox.currentText()
        ta_dir = self.dlg.TbpRasterComboBox.currentText()
        aeti_dir = self.dlg.AetiRasterComboBox.currentText()

        output_name = self.dlg.outputIndicName.text()+".tif"

        if self.indicator_key is 'Equity':
            self.indic_calc.equity(raster=tbp_name)
        elif self.indicator_key is 'Beneficial Fraction':
            self.indic_calc.beneficial_fraction(aeti_dir, ta_dir, output_name)
        elif self.indicator_key is 'Adequacy':
            self.indic_calc.adequacy(aeti_dir, ta_dir, output_name)
        elif self.indicator_key is 'Relative Water Deficit':
            self.indic_calc.relative_water_deficit(aeti_dir, output_name)
        else:
            raise NotImplementedError("Indicator: '{}' not implemented yet.".format(self.indicator))
        
        # self.canv_manag.add_rast(tbp_name)
        # self.canv_manag.add_rast(aeti_name)
        self.canv_manag.add_rast(output_name)


    def run(self):
        """Run method that performs all the real work"""
        # Create the dialog with elements (after translation) and keep reference
        # Only create GUI ONCE in callback, so that it will only load when the plugin is started
        if self.first_start == True:
            self.first_start = False
            self.dlg = WAPluginDialog()
            
            self.dlg.setWindowFlags(Qt.WindowStaysOnTopHint)
            self.dlg.indicatorListComboBox.addItems(INDICATORS_INFO.keys())

            self.coord_selc_tool = CoordinatesSelectorTool(self.iface.mapCanvas(),
                                                           self.dlg.TestCanvasLabel,
                                                           self.dlg.savePolygonButton)

            self.dlg.downloadButton.setEnabled(False)

            self.dlg.saveTokenButton.setEnabled(False)
            
            self.dlg.savePolygonButton.setEnabled(False)
            self.dlg.resetToolButton.setEnabled(False)

            self.dlg.signinButton.clicked.connect(self.signin)
            self.dlg.saveTokenButton.clicked.connect(self.saveToken)
            self.dlg.loadTokenButton.clicked.connect(self.loadToken)

            self.dlg.downloadButton.clicked.connect(self.downloadCropedRaster)
            self.dlg.loadRasterButton.clicked.connect(self.loadRaster)
            self.dlg.RasterRefreshButton.clicked.connect(self.listRasterMemory)

            self.dlg.workspaceComboBox.currentIndexChanged.connect(self.workspaceChange)
            self.dlg.cubeComboBox.currentIndexChanged.connect(self.cubeChange)
            self.dlg.dimensionComboBox.currentIndexChanged.connect(self.dimensionChange)
            self.dlg.memberComboBox.currentIndexChanged.connect(self.memberChange)
            self.dlg.measureComboBox.currentIndexChanged.connect(self.measureChange)
            # self.dlg.startDate.dateChanged.connect(self.onStartDateChanged)
            # self.dlg.endDate.dateChanged.connect(self.onEndDateChanged)

            self.dlg.indicatorListComboBox.currentIndexChanged.connect(self.indicatorChange)
            self.dlg.calculateButton.clicked.connect(self.calculateIndex)
            # self.dlg.tabWidget.currentChanged.connect(self.refreshRasters)

            self.dlg.getEdgesButton.clicked.connect(self.selectCoordinatesTool)
            self.dlg.savePolygonButton.clicked.connect(self.savePolygon)
            self.dlg.resetToolButton.clicked.connect(self.resetTool)

            self.listWorkspaces()
            self.listRasterMemory()
            self.indicatorChange()

            self.queryCoordinates = None

        # show the dialog
        self.dlg.show()
        # Run the dialog event loop
        result = self.dlg.exec_()
        # See if OK was pressed
        if result:
            # Do something useful here - delete the line containing pass and
            # substitute with your code.
            pass