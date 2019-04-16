#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
jmLightToolkit is a free toolkit in python I have written for managing lighting in Maya for my personal projects.
Feel free to use it in your own projects or in production. (Optimized for MtoA)
"""

from maya.app.general.mayaMixin import MayaQWidgetDockableMixin
from PySide2 import QtWidgets, QtGui, QtCore
from maya import OpenMayaUI as omui
from shiboken2 import getCppPointer
from functools import partial
import pymel.core as pm
import logging
import os
import sys
import math
import re

__author__      = 'Jason Mertens'
__copyright__   = 'Copyright (c) 2019 Jason Mertens'
__license__     = 'MIT'
__version__     = '2.0'
__email__       = 'mertens.jas@gmail.com'

MAIN_WINDOW = None
LOOK_WINDOW = None
FLTR_WINDOW = None
CUSTOM_IDX  = 32
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))

logger = logging.getLogger(__name__)

if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)

from jmLightToolkitUI import Ui_widget_root
from jmLightToolkitUI import Ui_widget_lightOptimizerItem
from jmLightToolkitUI import Ui_widget_unusedFiltersList
from jmLightToolkitUI import Ui_widget_unusedFiltersItem


class JMLightToolkit(MayaQWidgetDockableMixin, QtWidgets.QWidget, Ui_widget_root):
    """ Main Light Toolkit UI. """
    def __init__(self, parent=None):
        """ Initialize JMLightToolkit """
        super(JMLightToolkit, self).__init__(parent=parent)
        self.setWindowFlags(QtCore.Qt.Tool)
        self.setupUi(self)
        self.setWindowTitle(__name__)
        self.setObjectName(__name__)

        self.displayed_layer_name = "displayedLights"
        self.muted_layer_name = "mutedLights"
        self.mtoa_utils_grp = "mtoaUtils_C_001_GRUP"
        self.display_radius_grp = "displayRadius_C_001_GRUP"
        self.display_blocker_grp = "displayBlocker_C_001_GRUP"
        self.display_decay_near_grp = "displayDecayNear_C_001_GRUP"
        self.display_decay_far_grp = "displayDecayFar_C_001_GRUP"
        self.color_picked = [1.0, 1.0, 1.0]  # Maya Color Picker
        self.css_btn_on = "QPushButton{color:rgb(250,220,120)}"
        self.css_btn_default = "QPushButton{color:rgb(255,255,255)}"
        self.default_stylesheet = "QPushButton::checked{background-color:rgb(97,97,97); color:rgb(255,255,255); border:none}"

        self.lgt_types_default = [
            "pointLight",
            "spotLight",
            "areaLight",
            "directionalLight",
            "volumeLight" ]

        self.lgt_types_arnold = [
            "aiAreaLight",
            "aiMeshLight",
            "aiPhotometricLight",
            "aiSkyDomeLight" ]

        self.lgt_attrs_default = [
            "coneAngle",
            "penumbraAngle",
            "transmission",
            "dropoff",
            "decayRate",
            "emitDiffuse",
            "emitSpecular",
            "intensity",
            "shadowColor",
            "fogSpread",
            "fogIntensity",
            "camera",
            "format",
            "portalMode",
            "color" ]

        self.lgt_attrs_arnold = [
            "aiExposure",
            "aiSamples",
            "aiUseColorTemperature",
            "aiColorTemperature",
            "aiRadius",
            "aiAngle",
            "aiSpread",
            "aiDiffuse",
            "aiSpecular",
            "aiSss",
            "aiIndirect",
            "aiVolume",
            "aiMaxBounces",
            "aiNormalize",
            "aiRoundness",
            "aiCastShadows",
            "aiShadowDensity",
            "aiAspectRatio",
            "aiLensRadius",
            "aiVolumeSamples",
            "aiCastVolumetricShadows",
            "aiNormalize",
            "aiShadowColor",
            "aiShadowDensity" ]

        self.transform_attrs = [
            "translateX", "translateY", "translateZ",
            "rotateX", "rotateY", "rotateZ",
            "scaleX", "scaleY", "scaleZ" ]

        self.optimize_attrs = [
            "aiSamples",
            "aiIndirect",
            "aiMaxBounces",
            "aiRadius",
            "aiVolumeSamples",
            "aiVolume",
            "aiExposure",
            "intensity" ]

        # Clear list and sort UI if MtoA is not loaded
        if not pm.pluginInfo("mtoa", q=True, loaded=True):
            self.lgt_types_arnold = []
            self.lgt_attrs_arnold = []
            self.label_mtoaUtils.hide()
            self.pushButton_arnoldRenderView.hide()
            self.pushButton_transfertLightFilters.hide()
            self.pushButton_multiBlocker.hide()
            self.pushButton_multiDecay.hide()
            self.pushButton_multiGobo.hide()
            self.pushButton_displayRadius.hide()
            self.pushButton_deleteDisplayRadius.hide()
            self.pushButton_displayBlocker.hide()
            self.pushButton_deleteDisplayBlocker.hide()
            self.pushButton_displayNearDecay.hide()
            self.pushButton_displayFarDecay.hide()
            self.pushButton_deleteDisplayDecay.hide()
            self.pushButton_deleteUnusedBlocker.hide()
            self.pushButton_deleteUnusedDecay.hide()

        self.lgt_types = self.lgt_types_default + self.lgt_types_arnold
        self.lgt_attrs = self.lgt_attrs_default + self.lgt_attrs_arnold

        # Icons
        getIcon = lambda icon_name : QtGui.QIcon(os.path.join(PROJECT_DIR, "resources", "icons", icon_name))
        self.icon_blank = getIcon("icon_blank.png")
        self.icon_hierarchy_off = getIcon("icon_hierarchy_off.png")
        self.icon_hierarchy_on = getIcon("icon_hierarchy_on.png")
        self.icon_window_off = getIcon("icon_window_off.png")
        self.icon_window_on = getIcon("icon_window_on.png")
        self.icon_refresh = getIcon("icon_refresh.png")
        self.icon_inverse = getIcon("icon_inverse.png")
        self.icon_select = getIcon("icon_select.png")
        self.icon_sync_off = getIcon("icon_sync_off.png")
        self.icon_sync_on = getIcon("icon_sync_on.png")
        self.icon_spotlight = getIcon("spotLight.svg")
        self.icon_pointLight = getIcon("pointLight.svg")
        self.icon_directionalLight = getIcon("directionalLight.svg")
        self.icon_areaLight = getIcon("areaLight.svg")
        self.icon_volumeLight = getIcon("volumeLight.svg")
        self.icon_ambientLight = getIcon("ambientLight.svg")
        self.icon_aiAreaLight = getIcon("aiAreaLight.svg")
        self.icon_aiLightPortal = getIcon("aiLightPortal.svg")
        self.icon_aiMeshLight = getIcon("aiMeshLight.svg")
        self.icon_aiPhotometricLight = getIcon("aiPhotometricLight.svg")
        self.icon_aiPhysicalLight = getIcon("aiPhysicalLight.svg")
        self.icon_aiSkyDomeLight = getIcon("aiSkyDomeLight.svg")

        # Connect Methods to UI
        self.pushButton_soloLights.clicked.connect(self.soloLights)
        self.pushButton_muteLights.clicked.connect(self.muteLights)
        self.pushButton_restoreLights.clicked.connect(self.restoreLights)
        self.pushButton_soloLights_hierarchy.clicked.connect(self.__hierarchyCSS)
        self.pushButton_lookThrough.clicked.connect(self.lookThrough)
        self.pushButton_lookThroughWindow.clicked.connect(self.__lookThroughCSS)
        self.pushButton_quickAlign.clicked.connect(self.quickAlign)
        self.pushButton_quickAlign_T.clicked.connect(self.__quickAlignCSS)
        self.pushButton_quickAlign_R.clicked.connect(self.__quickAlignCSS)
        self.pushButton_quickAlign_S.clicked.connect(self.__quickAlignCSS)
        self.pushButton_selectAllLights.clicked.connect(self.selectAllLights)

        self.pushButton_multiAttr_refresh.clicked.connect(self.getMultiAttributesLights)
        self.pushButton_setNewValue.clicked.connect(partial(self.setMultiAttributesLights, "absolute"))
        self.pushButton_incrementeValue.clicked.connect(partial(self.setMultiAttributesLights, "relative"))
        self.pushButton_multiAttr_inverse.clicked.connect(self.__inverseValueMultiAttributes)
        self.pushButton_multiAttr_setStep.clicked.connect(self.__setStepMultiAttributes)
        self.pushButton_multiAttr_refresh.setIcon(self.icon_refresh)
        self.pushButton_multiAttr_inverse.setIcon(self.icon_inverse)
        self.pushButton_colorPicker.setStyleSheet("QPushButton{background-color:#ffffff;}")
        self.pushButton_colorPicker.clicked.connect(self.openMayaColorPicker)
        self.pushButton_setColorAttribute.clicked.connect(self.setColorPicked)
        self.pushButton_transfertLightAttributes.clicked.connect(self.transfertLightAttrs)

        self.pushButton_createSet.clicked.connect(self.createSet)
        self.pushButton_makeLights.clicked.connect(self.makeLightLinks)
        self.pushButton_breakLights.clicked.connect(self.breakLightLinks)
        self.pushButton_selectLinked.clicked.connect(self.selectLinked)
        self.pushButton_breakAllLinks.clicked.connect(self.breakAllLinks)
        self.pushButton_transfertLightsLinks.clicked.connect(self.transfertLightLinks)

        self.pushButton_arnoldRenderView.clicked.connect(self.openArnoldRenderView)
        self.pushButton_transfertLightFilters.clicked.connect(self.transfertLightFilters)
        self.pushButton_multiBlocker.clicked.connect(partial(self.linkLightFilterToLights, "aiLightBlocker"))
        self.pushButton_multiDecay.clicked.connect(partial(self.linkLightFilterToLights, "aiLightDecay"))
        self.pushButton_multiGobo.clicked.connect(partial(self.linkLightFilterToLights, "aiGobo"))
        self.pushButton_displayRadius.clicked.connect(self.displayRadius)
        self.pushButton_deleteDisplayRadius.clicked.connect(self.deleteDisplayRadius)
        self.pushButton_displayBlocker.clicked.connect(self.displayBlocker)
        self.pushButton_deleteDisplayBlocker.clicked.connect(self.deleteDisplayBlocker)
        self.pushButton_displayNearDecay.clicked.connect(partial(self.displayDecay, "near"))
        self.pushButton_displayFarDecay.clicked.connect(partial(self.displayDecay, "far"))
        self.pushButton_deleteDisplayDecay.clicked.connect(self.deleteDisplayDecay)

        self.pushButton_colorOutliner_R.clicked.connect(partial(self.colorOutlinerSelected, "red"))
        self.pushButton_colorOutliner_O.clicked.connect(partial(self.colorOutlinerSelected, "orange"))
        self.pushButton_colorOutliner_Y.clicked.connect(partial(self.colorOutlinerSelected, "yellow"))
        self.pushButton_colorOutliner_G.clicked.connect(partial(self.colorOutlinerSelected, "green"))
        self.pushButton_colorOutliner_T.clicked.connect(partial(self.colorOutlinerSelected, "turquoise"))
        self.pushButton_colorOutliner_C.clicked.connect(partial(self.colorOutlinerSelected, "cyan"))
        self.pushButton_colorOutliner_B.clicked.connect(partial(self.colorOutlinerSelected, "blue"))
        self.pushButton_colorOutliner_P.clicked.connect(partial(self.colorOutlinerSelected, "purple"))
        self.pushButton_colorOutliner_M.clicked.connect(partial(self.colorOutlinerSelected, "magenta"))
        self.pushButton_colorOutliner_none.clicked.connect(partial(self.colorOutlinerSelected, "black", False))
        self.pushButton_colorOutliner_R.setStyleSheet("QPushButton{background-color:#FF8080;}")
        self.pushButton_colorOutliner_O.setStyleSheet("QPushButton{background-color:#FFCC50;}")
        self.pushButton_colorOutliner_Y.setStyleSheet("QPushButton{background-color:#FFFF80;}")
        self.pushButton_colorOutliner_G.setStyleSheet("QPushButton{background-color:#90FF70;}")
        self.pushButton_colorOutliner_T.setStyleSheet("QPushButton{background-color:#40FFCC;}")
        self.pushButton_colorOutliner_C.setStyleSheet("QPushButton{background-color:#80FFFF;}")
        self.pushButton_colorOutliner_B.setStyleSheet("QPushButton{background-color:#50BBFF;}")
        self.pushButton_colorOutliner_P.setStyleSheet("QPushButton{background-color:#BB50FF;}")
        self.pushButton_colorOutliner_M.setStyleSheet("QPushButton{background-color:#FF80FF;}")
        self.pushButton_colorOutliner_none.setStyleSheet("QPushButton{background-color:#ffffff;}")

        self.pushButton_advancedSelection_select.clicked.connect(self.advancedSelection)
        self.pushButton_advancedSelection_select.setIcon(self.icon_select)
        self.groupBox_radio_1.setStyleSheet("QGroupBox{background-color:#444444; border: 0px solid #444444;}")
        self.groupBox_radio_2.setStyleSheet("QGroupBox{background-color:#444444; border: 0px solid #444444;}")
        self.autocompletion = self.lgt_types + ["mesh","aiStandIn"]
        self.completer = QtWidgets.QCompleter()
        self.completer.setModel(QtGui.QStringListModel(self.autocompletion))
        self.lineEdit_advancedSelection_type.setCompleter(self.completer)
        self.lineEdit_advancedSelection_type.insert("mesh,aiStandIn")

        self.pushButton_selectChildren.clicked.connect(self.selectChildren)
        self.pushButton_selectNotIlluminatingLights.clicked.connect(self.selectNotIlluminatingLights)
        self.pushButton_deleteUnusedBlocker.clicked.connect(partial(self.deleteSafelyLightFilter, "aiLightBlocker"))
        self.pushButton_deleteUnusedDecay.clicked.connect(partial(self.deleteSafelyLightFilter, "aiLightDecay"))

        self.horizontalSlider_lightOptimizer_min.valueChanged[int].connect(self.spinBox_lightOptimizer_min.setValue)
        self.spinBox_lightOptimizer_min.valueChanged[int].connect(self.horizontalSlider_lightOptimizer_min.setValue)
        self.spinBox_lightOptimizer_min.valueChanged[int].connect(self.horizontalSlider_lightOptimizer_min.valueChanged)
        self.horizontalSlider_lightOptimizer_max.valueChanged[int].connect(self.spinBox_lightOptimizer_max.setValue)
        self.spinBox_lightOptimizer_max.valueChanged[int].connect(self.horizontalSlider_lightOptimizer_max.setValue)
        self.spinBox_lightOptimizer_max.valueChanged[int].connect(self.horizontalSlider_lightOptimizer_max.valueChanged)
        self.pushButton_lightOptimizer_sync.setStyleSheet(self.default_stylesheet)
        self.pushButton_lightOptimizer_sync.setIcon(self.icon_sync_off)

        self.pushButton_lightOptimizer_setValue.clicked.connect(self.lightOptimizer__setMultiplesValues)
        self.pushButton_lightOptimizer_selectLights.clicked.connect(self.lightOptimizer__selectLightsFromList)
        self.comboBox_lightOptimizer_attributes.currentIndexChanged.connect(self.__lightOptimizer__adaptSlider)
        self.pushButton_lightOptimizer_sync.clicked.connect(self.__lightOptimizer__toggleSync)

        # Pre-build Methods
        self.__populateComboBoxAttributes()
        self.__lightOptimizer__populateComboBox()
        self.__soloMuteLightsCSS()
        self.__hierarchyCSS()
        self.__lookThroughCSS()
        self.__quickAlignCSS()
        self.__displayRadiusCSS()
        self.__displayBlockerCSS()
        self.__displayDecayCSS()

    def keyPressEvent(self, event):
        """ Keyboard mapping. """
        if event.key() == QtCore.Qt.Key_Shift:
            pass

    def _wrapperUndoChunck(function):
        """ Create an undo Chunk and wrap it. """
        def wrapper(self, *args, **kwargs):
            try:
                pm.undoInfo(openChunk=True)
                function(self, *args, **kwargs)
            finally:
                pm.undoInfo(closeChunk=True)

        return wrapper

    def _wrapperSelected(function):
        """ Recover selection. """
        def wrapper(self, *args, **kwargs):
            selected = None
            try:
                selected = pm.selected()
                function(self, *args, **kwargs)
            finally:
                pm.select(selected)

        return wrapper

    @_wrapperUndoChunck
    @_wrapperSelected
    def soloLights(self):
        """ Put lights selected in 'displayed lights' display layer.

            Returns:
                (list): Displayed lights.
        """
        self.restoreLights()
        is_hierarchy = self.pushButton_soloLights_hierarchy.isChecked()
        lights = { "displayed" : self._onlyLightsFromSelection(all_hierachy=is_hierarchy), "muted" : [] }

        # Return if lists them empty
        if not lights["displayed"]:
            return None

        # Get unselected lights
        all_lights = self._getAllLights()
        lights["muted"] = list(set(all_lights).difference(lights["displayed"]))

        # Create Display layer
        pm.select(clear=True)
        muted_layer = pm.createDisplayLayer(n=self.muted_layer_name)
        muted_layer.addMembers(lights["muted"])
        muted_layer.color.set(21)
        muted_layer.visibility.set(0)

        displayed_layer = pm.createDisplayLayer(n=self.displayed_layer_name)
        displayed_layer.addMembers(lights["displayed"])
        displayed_layer.color.set(22)

        self.__soloMuteLightsCSS()
        logger.info("Lights displayed : %s" % [lgt.name() for lgt in lights["displayed"]])
        return lights["displayed"]

    @_wrapperUndoChunck
    @_wrapperSelected
    def muteLights(self):
        """ Put lights selected in 'muted lights' display layer.

            Returns:
                (list): Muted lights.
        """
        is_hierarchy = self.pushButton_soloLights_hierarchy.isChecked()
        lights = self._onlyLightsFromSelection(all_hierachy=is_hierarchy)

        # Return if list is empty
        if not lights:
            return None

        # Create Display layer either get it
        if pm.objExists(self.muted_layer_name):
            pm.PyNode(self.muted_layer_name).addMembers(lights)
        else:
            pm.select(clear=True)
            muted_layer = pm.createDisplayLayer(n=self.muted_layer_name)
            muted_layer.addMembers(lights)
            muted_layer.color.set(21)
            muted_layer.visibility.set(0)

        self.__soloMuteLightsCSS()
        logger.info("Lights muted : %s" % [lgt.name() for lgt in lights])
        return lights

    @_wrapperUndoChunck
    def restoreLights(self):
        """ Delete Displayed/Muted display layer. """
        something_deleted = False
        if pm.objExists(self.displayed_layer_name):
            pm.delete(self.displayed_layer_name)
            something_deleted = True

        if pm.objExists(self.muted_layer_name):
            pm.delete(self.muted_layer_name)
            something_deleted = True

        if something_deleted:
            self.__soloMuteLightsCSS()
            logger.info("Lights visibilities restored.")
            return True
        else:
            return False

    def __soloMuteLightsCSS(self):
        """ Solo/Mute Lights look. """
        if pm.objExists(self.displayed_layer_name):
            self.pushButton_soloLights.setStyleSheet(self.css_btn_on)
        else:
            self.pushButton_soloLights.setStyleSheet(self.css_btn_default)

        if pm.objExists(self.muted_layer_name):
            self.pushButton_muteLights.setStyleSheet(self.css_btn_on)
        else:
            self.pushButton_muteLights.setStyleSheet(self.css_btn_default)

    def __hierarchyCSS(self):
        """ Stylize hierarchy button """
        if self.pushButton_soloLights_hierarchy.isChecked():
            self.pushButton_soloLights_hierarchy.setStyleSheet(self.default_stylesheet)
            self.pushButton_soloLights_hierarchy.setIcon(self.icon_hierarchy_on)

        else:
            self.pushButton_soloLights_hierarchy.setStyleSheet(self.default_stylesheet)
            self.pushButton_soloLights_hierarchy.setIcon(self.icon_hierarchy_off)

    @_wrapperUndoChunck
    def lookThrough(self):
        """ Light lookthrough. """
        # If already Through, delete cam
        looked_through = self._isLookThrough()
        if looked_through is not None:
            pm.delete(looked_through)
            self.__lookThroughCSS()
            return

        # Look Through Window
        if self.pushButton_lookThroughWindow.isChecked():
            createLookThroughWindow()
            self.__lookThroughCSS()
            return

        # Get Panel, if persp found, throught this cam
        all_panels = [ui for ui in pm.getPanel(vis=True) if "modelPanel" in ui.name()]
        current_panel = None
        for panel in all_panels:
            if "persp" in pm.windows.modelPanel(panel, query=True, camera=True):
                current_panel = panel
                break

        else:  # if modelPanel4 find, throught this cam
            for panel in all_panels:
                if panel.name() == "modelPanel4":
                    current_panel = panel
                    break
            else:
                current_panel = all_panels[-1]

        # See Trough
        lights = self._onlyLightsFromSelection()
        if lights:
            light =  lights[0].name()
            cmd = "lookThroughModelPanelClipped(\"" + light + "\", \"" + current_panel + "\", 0.001, 10000)"
            pm.mel.eval(cmd)
            logger.info("Look through : %s" % light)

        self.__lookThroughCSS()

    def _isLookThrough(self):
        """ Get looked through camera.

            Returns:
                (camera): looked through camera
        """
        looked_through = None
        for cam in pm.ls(ca=True):
            shape = cam.getParent().getShape()
            if shape is None:
                continue

            if pm.nodeType(shape) in self.lgt_types:
                looked_through = cam
                break

        return looked_through

    def __lookThroughCSS(self):
        """ Stylize lookthrough button """
        # Window icon
        if self.pushButton_lookThroughWindow.isChecked():
            self.pushButton_lookThroughWindow.setStyleSheet(self.default_stylesheet)
            self.pushButton_lookThroughWindow.setIcon(self.icon_window_on)

        else:
            self.pushButton_lookThroughWindow.setStyleSheet(self.default_stylesheet)
            self.pushButton_lookThroughWindow.setIcon(self.icon_window_off)

        # Stylize button
        if self._isLookThrough() is not None:
            self.pushButton_lookThrough.setStyleSheet(self.css_btn_on)
        else:
            self.pushButton_lookThrough.setStyleSheet(self.css_btn_default)

    @_wrapperUndoChunck
    def quickAlign(self):
        """ Quick Align like 3DS Max. """
        # Get checkbox value
        t_ = self.pushButton_quickAlign_T.isChecked()
        r_ = self.pushButton_quickAlign_R.isChecked()
        s_ = self.pushButton_quickAlign_S.isChecked()

        # Return if no one checkbox checked
        if not t_ and not r_ and not s_:
            logger.warning("Nothing checked in UI")
            return None

        # Get selection then check it
        selected = pm.selected()
        if not selected:
            logger.warning("Nothing selected")
            return None

        elif len(selected) < 2:
            logger.warning("Only one object selected")
            return None

        master = selected[-1]
        slaves = selected[:-1]
        if t_:  # Match translation
            for slave in slaves :
                pm.matchTransform(slave, master, position=True)

        if r_:  # Match rotation
            for slave in slaves :
                pm.matchTransform(slave, master, rotation=True)

        if s_:  # Match scale
            for slave in slaves :
                pm.matchTransform(slave, master, scale=True)

        pm.select(slaves)
        logger.info("%s aligned to %s" % (slaves, master))
        return True

    def __quickAlignCSS(self):
        """ Stylize XYZ quick align buttons """
        # CSS preset
        red_stylesheet = "QPushButton{background-color:rgb(220,80,120); color:rgb(255,200,200); border:none}"
        grn_stylesheet = "QPushButton{background:rgb(80,220,120); color:rgb(200,255,200); border:none}"
        blu_stylesheet = "QPushButton{background:rgb(80,120,220); color:rgb(200,200,255); border:none}"
        default_stylesheet = "QPushButton{background:rgb(97,97,97); color:rgb(255,255,255)}"

        # Reset style
        self.pushButton_quickAlign_T.setStyleSheet(default_stylesheet)
        self.pushButton_quickAlign_R.setStyleSheet(default_stylesheet)
        self.pushButton_quickAlign_S.setStyleSheet(default_stylesheet)

        # Stylize
        if self.pushButton_quickAlign_T.isChecked():
            self.pushButton_quickAlign_T.setStyleSheet(red_stylesheet)

        if self.pushButton_quickAlign_R.isChecked():
            self.pushButton_quickAlign_R.setStyleSheet(grn_stylesheet)

        if self.pushButton_quickAlign_S.isChecked():
            self.pushButton_quickAlign_S.setStyleSheet(blu_stylesheet)

    def selectAllLights(self):
        """ Select all standard/Arnold lights from scene """
        all_lights = self._getAllLights()
        pm.select(all_lights, add=True)
        return all_lights

    def getMultiAttributesLights(self):
        """ Get multi attributes on a group of lights selected """
        lights = self._onlyLightsFromSelection()
        if not lights:
            return None

        num_lights = len(lights)
        attributes_kept = []

        for attr_ in self.lgt_attrs:
            attr_exist = 0
            for light in lights:
                if pm.objExists("%s.%s" % (light, attr_)):
                    attr_exist += 1

                if attr_exist == num_lights:
                    attributes_kept.append(attr_)

        # Populate Attrs Combo box
        self.comboBox_multiAttr.clear()
        for attr_ in attributes_kept:
            self.comboBox_multiAttr.addItem(self.icon_blank, attr_)

        # Add Sperator
        number_element = self.comboBox_multiAttr.count()
        if number_element:
            self.comboBox_multiAttr.insertSeparator(number_element)

        # Populate Transform Attrs Combo box
        for attr_ in self.transform_attrs:
            self.comboBox_multiAttr.addItem(self.icon_blank, attr_)

        logger.info("Attributes filtered")
        return attributes_kept

    @_wrapperUndoChunck
    def setMultiAttributesLights(self, mode):
        """ Set multi attributes on a group of lights selected.

            Args:
                mode(str): Choose either 'absolute' for new value or 'relative' for increment value.
        """
        if mode not in ["absolute", "relative"]:
            logger.error("Choose either 'absolute' for new value or 'relative' for increment value.")
            return None

        lights = self._onlyLightsFromSelection(get_shapes=True)
        if not lights:
            return None

        attr_ = self.comboBox_multiAttr.currentText()
        value = self.doubleSpinBox_multiAttr.value()

        # Light Attributes
        if attr_ in self.lgt_attrs:
            for light in lights:
                if pm.objExists("%s.%s" % (light, attr_)):
                    if mode == "absolute":
                        pm.setAttr("%s.%s" % (light, attr_), value)
                    elif mode == "relative":
                        current_value = pm.getAttr("%s.%s" % (light, attr_))
                        pm.setAttr("%s.%s" % (light, attr_), value + current_value)
                else:
                    logger.warning("%s.%s doesn't exist" % (light, attr_))

        # Transform Attributes
        else:  # attr_ in self.transform_data
            for selected in pm.selected():
                if pm.nodeType(selected.name()) != "transform":
                    selected = selected.getParent()

                if pm.objExists("%s.%s" % (selected, attr_)):
                    if mode == "absolute":
                        pm.setAttr("%s.%s" % (selected, attr_), value)
                    elif mode == "relative":
                        current_value = pm.getAttr("%s.%s" % (selected, attr_))
                        pm.setAttr("%s.%s" % (selected, attr_), value + current_value)
                else:
                    logger.warning("%s.%s doesn't exist" % (selected, attr_))

        logger.info("'Multi set attributes' success")
        return {"lights" : lights, "attribute" : attr_, "value" : value}

    def __populateComboBoxAttributes(self):
        """ Populate combo Box in Ui at started. """
        for attr_ in self.lgt_attrs:
            self.comboBox_multiAttr.addItem(self.icon_blank, attr_)

        self.comboBox_multiAttr.insertSeparator(self.comboBox_multiAttr.count())
        for attr_ in self.transform_attrs:
            self.comboBox_multiAttr.addItem(self.icon_blank, attr_)

    def __inverseValueMultiAttributes(self):
        """ Inverse float box value. """
        value = self.doubleSpinBox_multiAttr.value()
        if value > 0:
            self.doubleSpinBox_multiAttr.setValue(-value)

        elif value < 0:
            self.doubleSpinBox_multiAttr.setValue(math.fabs(value))

    def __setStepMultiAttributes(self):
        """ Choose either step 0.5 or step 0.1. """
        if self.doubleSpinBox_multiAttr.singleStep() == 0.5:
            self.doubleSpinBox_multiAttr.setSingleStep(0.1)
            self.pushButton_multiAttr_setStep.setText("0.1")

        elif self.doubleSpinBox_multiAttr.singleStep() == 0.1:
            self.doubleSpinBox_multiAttr.setSingleStep(0.5)
            self.pushButton_multiAttr_setStep.setText("0.5")

    def openMayaColorPicker(self):
        """ Open Maya UI Color Picker. """
        save_color = self.color_picked
        cursor_position = QtGui.QCursor.pos()

        # Pick color
        self.color_picked = pm.cmds.colorEditor(mini=True, rgb=save_color, pos=(cursor_position.x(), cursor_position.y()))
        self.color_picked = [color for color in self.color_picked.split(" ") if color]
        self.color_picked = [float(color) for color in self.color_picked]
        self.color_picked = self.color_picked[:-1]

        if not self.color_picked[0] and not self.color_picked[1] and not self.color_picked[2]:
            self.color_picked = save_color

        color_R = self.color_picked[0] * 255.0
        color_G = self.color_picked[1] * 255.0
        color_B = self.color_picked[2] * 255.0
        color = "{0}, {1}, {2}".format(color_R, color_G, color_B)

        self.pushButton_colorPicker.setStyleSheet("QPushButton{background-color:rgb(%s);}" % color)
        logger.info("R=%s G=%s B=%s" % (self.color_picked[0], self.color_picked[1], self.color_picked[2]))
        return self.color_picked

    @_wrapperUndoChunck
    def setColorPicked(self):
        """ Set lights color. """
        for light in self._onlyLightsFromSelection():
            pm.setAttr("%s.color" % light, self.color_picked)
            logger.info("Color : %s" % self.color_picked)

    @_wrapperUndoChunck
    def transfertLightAttrs(self):
        """ Transfert attributes from first light selected to others light(s) selected. """
        # Get lights
        lights = self._onlyLightsFromSelection(get_shapes=True)
        if not lights:
            return None

        driver = lights[0]
        slaves = lights[1:]
        copy_attr = None

        for attr_ in self.lgt_attrs:
            # Copy attributes
            if pm.objExists("%s.%s" % (driver, attr_)):
                copy_attr = pm.getAttr("%s.%s" % (driver, attr_))
            else:
                continue

            # Set attributes
            for slave in slaves:
                if pm.objExists("%s.%s" % (slave, attr_)):
                    pm.setAttr("%s.%s" % (slave, attr_), copy_attr)

        pm.select(slaves)
        logger.info("%s attributes transfered to %s" % (driver.name(), [node.name() for node in slaves]))
        return True

    @_wrapperUndoChunck
    def createSet(self):
        """ Create Set then put transform node selected. """
        # GET SELECTED
        include_type = ["mesh", "aiStandIn", "pgYetiMaya"]
        selected = pm.selected()
        pre_setname = selected[-1].name().split("_")[0]

        shapes = []
        for node in selected:
            shapes.extend([node for node in node.getChildren(ad=True, s=True) if pm.nodeType(node.name()) in include_type])

        transforms = [shape.getParent() for shape in shapes]

        if not transforms:
            logger.warning("Invalid selection")
            return None

        # Prompt Dialog
        result = pm.promptDialog(
            title='Create Set',
            message='Name:',
            button=['OK', 'Cancel'],
            defaultButton='OK',
            cancelButton='Cancel',
            dismissString='Cancel',
            text=pre_setname,
        )

        if result == 'OK':
            input_ = pm.promptDialog(query=True, text=True)
        else:
            logger.warning("Set need a name")
            return None

        # ROOT SET
        if pm.objExists("root_SETS"):
            root_set = pm.PyNode("root_SETS")
        else:
            pm.select(cl=True)
            root_set = pm.sets(n="root_SETS")

        # CREATE SET
        if re.search(r'[A-Za-z0-9_]+(_SETS)', input_) is None:
            input_ = "%s_SET" % input_

        pm.select(cl=True)
        set_ = pm.sets(n=input_)
        set_.addMembers(transforms)
        pm.sets(root_set, fe=set_)

        pm.select(selected)
        logger.info("%s" % set_)
        return set_

    @_wrapperSelected
    def makeLightLinks(self):
        """ cmds.MakeLightLinks Maya Command. Link only to transform. """
        selected = pm.selected()
        set_children = []
        for node in selected:
            if pm.nodeType(node) == "objectSet":
                set_children.extend(node.members(True))
                selected.remove(node)

        pm.select(selected)
        pm.select(set_children, add=True)
        pm.cmds.MakeLightLinks()
        logger.info("lights linked")

    @_wrapperSelected
    def breakLightLinks(self):
        """ cmds.BreakLightLinks Maya Command """
        selected = pm.selected()
        set_children = []
        for node in selected:
            if pm.nodeType(node) == "objectSet":
                set_children.extend(node.members(True))
                selected.remove(node)

        pm.select(selected)
        pm.select(set_children, add=True)
        pm.cmds.BreakLightLinks()
        logger.info("lights breaked")

    def selectLinked(self):
        """ Toggle function between:
            pm.cmds.SelectLightsIlluminatingObject()
            pm.cmds.SelectObjectsIlluminatedByLight()
        """
        selected = pm.selected()
        if not selected:
            logger.warning("Nothing selected")
            return None

        if pm.nodeType(pm.selected()[0].getShape().name()) in self.lgt_types:
            pm.cmds.SelectObjectsIlluminatedByLight()
            if not pm.selected():
                logger.warning("%s illuminate nothing" % [node.name() for node in selected])
                pm.select(selected)
                return None
        else:
            pm.cmds.SelectLightsIlluminatingObject()
            if not pm.selected():
                logger.warning("%s is not illuminated" % [node.name() for node in selected])
                pm.select(selected)
                return None

        logger.info("link : %s " % [node.name() for node in pm.selected()])
        return selected

    def breakAllLinks(self):
        """ Unlink lights from all """
        lights = self._onlyLightsFromSelection()
        for light in lights:
            object_linked = pm.lightlink(q=True, light=light)
            pm.lightlink(light=light, object=object_linked, b=True)

        logger.info("%s breaked from all" % [node.name() for node in lights])
        return light

    @_wrapperUndoChunck
    def transfertLightLinks(self):
        """ Transfert all links from first light selected to others lights selected. """
        # Get lights selected
        lights = self._onlyLightsFromSelection()

        # Check light selection
        if not lights:
            logger.warning("Nothing selected")
            return None

        elif len(lights) < 2:
            logger.warning("Only one light selected")
            return None

        driver = lights[0]
        slaves = lights[1:]

        type_ = ["mesh", "aiStandIn", "pgYetiMaya"]
        object_linked = pm.lightlink(q=True, light=driver)
        sorted_link = [shape for shape in object_linked if pm.nodeType(shape) in type_]

        for slave in slaves:
            object_linked = pm.lightlink(light=slave)
            pm.lightlink(light=slave, object=object_linked, b=True)
            pm.lightlink(light=slave, object=sorted_link, m=True)

        pm.select(slaves)
        logger.info("Link from %s copyied to %s" % (driver.name(), [slave.name() for slave in slaves]))
        return True

    def openArnoldRenderView(self):
        """ Open Arnold Render View. """
        pm.mel.eval("cmdArnoldMtoARenderView")

    @_wrapperUndoChunck
    def transfertLightFilters(self):
        """ Transfert light filters from first light selected to others lights selected. """
        # Get lights
        lights = self._onlyLightsFromSelection(get_shapes=True)
        if not lights:
            return None

        driver = lights[0]
        slaves = lights[1:]
        copy_attr = None

        # Get driver connection
        i = 0
        driver_connection = {}
        is_connected = pm.connectionInfo("%s.aiFilters[%s]" % (driver, i), id=True)
        while is_connected:
            driver_connection["aiFilters[%s]" % i] = pm.connectionInfo("%s.aiFilters[%s]" % (driver, i), sfd=True).split(".")[0]
            i += 1
            is_connected = pm.connectionInfo("%s.aiFilters[%s]" % (driver, i), id=True)

        if not driver_connection:
            logger.warning("%s don't have any light filters")
            return None

        # Disconnect all light filters from the others lights
        lenght = len(driver_connection)
        for slave in slaves:
            i = 0
            is_connected = pm.connectionInfo("%s.aiFilters[%s]" % (slave, i), id=True)
            while is_connected:
                slave_connection = pm.connectionInfo("%s.aiFilters[%s]" % (slave, i), sfd=True)
                pm.PyNode(slave_connection) // pm.PyNode("%s.aiFilters[%s]" % (slave, i))
                i += 1
                is_connected = pm.connectionInfo("%s.aiFilters[%s]" % (slave, i), id=True)

            # Connect filters
            for key, value in driver_connection.items():
                pm.PyNode("%s.message" % value) >> pm.PyNode("%s.%s" % (slave.name(), key))

        pm.select(slaves)
        logger.info("%s light filters transfered to %s" % (driver.name(), [node.name() for node in slaves]))
        return driver_connection

    @_wrapperUndoChunck
    def linkLightFilterToLights(self, filter_):
        """ Either create or get light filter then link it to lights.

            Args:
                filter_(str): Light filter that you want. 'aiLightBlocker', 'aiLightDecay', 'aiGobo'.
        """
        # Check
        if filter_ not in ["aiLightDecay", "aiLightBlocker", "aiGobo"]:
            logger.error("'aiLightBlocker', 'aiLightDecay', 'aiGobo'")
            return None

        # Sort lights and filters
        lights_selected = []
        filter_selected = []
        for selected in pm.selected():
            if pm.nodeType(selected.name()) == "transform":
                if pm.nodeType(selected.getShape().name()) in self.lgt_types:
                    lights_selected.append(selected.getShape())

                elif pm.nodeType(selected.getShape().name()) == filter_:
                    filter_selected.append(selected.getShape())

            else:  # if selected != transform
                if pm.nodeType(selected.name()) in self.lgt_types:
                    lights_selected.append(selected)

                elif pm.nodeType(selected.name()) == filter_:
                    filter_selected.append(selected)

        # Return if no lights selected
        if not lights_selected:
            logger.warning("No lights found.")
            return None

        # If filter is empty, create one
        if not filter_selected:
            filter_selected = [pm.createNode(filter_)]

        # Link filter to lights
        for filtr in filter_selected:
            try:
                transform_filter = filtr.getParent()
            except AttributeError:
                transform_filter = filtr

            for lgt in lights_selected:
                if (filtr not in lgt.inputs()) and (transform_filter not in lgt.inputs()):
                    i = 0
                    info = pm.connectionInfo("%s.aiFilters[%s]" % (lgt, i), id=True)

                    while info :
                        i += 1
                        info = pm.connectionInfo("%s.aiFilters[%s]" % (lgt, i), id=True)

                    node_filter = pm.PyNode("%s.message" % filtr)
                    node_lgt = pm.PyNode("%s.aiFilters[%s]" % (lgt, i))
                    node_filter >> node_lgt

        filter_name = [node.name() for node in filter_selected]
        logger.info("filter : %s " % filter_name)
        return filter_selected

    @_wrapperUndoChunck
    @_wrapperSelected
    def displayRadius(self):
        """ Create 'aiRadius' display from lights selected. """
        save_selected = pm.selected()
        # Get lights
        lights = self._onlyLightsFromSelection()
        if not lights:
            return None

        # Create mtoa utils grp
        utils_grp = self._eitherCreateGetNode("grp", self.mtoa_utils_grp)
        display_radius_grp = self._eitherCreateGetNode("grp", self.display_radius_grp)
        pm.parent(display_radius_grp, utils_grp)

        # Create shader
        if not pm.objExists("displayRadius_SHAD"):
            shader = pm.shadingNode("lambert", n="displayRadius_SHAD", asShader=True)
            shading_group= pm.sets(renderable=True, n="displayRadius_SDEG", noSurfaceShader=True, empty=True)
            pm.connectAttr('%s.outColor' % shader, '%s.surfaceShader' % shading_group)
            shader.color.set(0.0, 0.6, 0.7)
            shader.transparency.set(0.9, 0.9, 0.9)
            shader.translucence.set(1)
        else:
            shader = pm.PyNode("displayRadius_SHAD")

        # Process
        pm.select(save_selected)
        out = []
        for light in lights:
            attr_radius = "%s.aiRadius" % light
            # reloop if aiRaius not exist
            if not pm.objExists(attr_radius):
                continue

            # Reloop if display alradeay exist
            if pm.PyNode(attr_radius).inputs(type="expression"):
                continue

            # Create Display
            display_mesh_name = re.sub(
                r"^(?P<lightname>[A-Za-z0-9]+)(?P<under>[_])(?P<utility>[a-zA-Z]*)(?P<left>[A-Za-z0-9_]+)$",
                r"\g<lightname>\g<under>displayRadius\g<left>",
                light.name())

            display_mesh = pm.polySphere(n=display_mesh_name, subdivisionsAxis=36, subdivisionsHeight=36)[0]

            # assign shader
            pm.select(display_mesh)
            pm.hyperShade(assign=shader)

            # set attr
            display_mesh_shape = display_mesh.getShape()
            display_mesh_shape.attr("castsShadows").set(0)
            display_mesh_shape.attr("receiveShadows").set(0)
            display_mesh_shape.attr("motionBlur").set(0)
            display_mesh_shape.attr("primaryVisibility").set(0)
            display_mesh_shape.attr("smoothShading").set(0)
            display_mesh_shape.attr("visibleInReflections").set(0)
            display_mesh_shape.attr("visibleInRefractions").set(0)
            display_mesh_shape.attr("doubleSided").set(0)
            display_mesh_shape.attr("aiOpaque").set(0)
            display_mesh_shape.attr("aiVisibleInDiffuseReflection").set(0)
            display_mesh_shape.attr("aiVisibleInSpecularReflection").set(0)
            display_mesh_shape.attr("aiVisibleInDiffuseTransmission").set(0)
            display_mesh_shape.attr("aiVisibleInSpecularTransmission").set(0)
            display_mesh_shape.attr("aiSelfShadows").set(0)

            # Rotate
            display_mesh.rotateX.set(90)
            pm.select(display_mesh)
            pm.makeIdentity(apply=True, t=1, r=1, s=1, n=0, pn=1)
            display_mesh.rotateOrder.set(2)

            # Align mesh to light
            pm.pointConstraint(light, display_mesh)
            pm.pointConstraint(light, display_mesh, rm=True)
            pm.orientConstraint(light, display_mesh)
            pm.orientConstraint(light, display_mesh, rm=True)

            # Create new local space
            local_space_name = re.sub(
                r"^(?P<lightname>[A-Za-z0-9]+)(?P<under>[_])(?P<utility>[a-zA-Z]*)(?P<left>[A-Za-z0-9_]+)$",
                r"\g<lightname>\g<under>localSpaceRadius\g<left>",
                light.name())

            local_space_group = pm.group(em=True, n=local_space_name)
            pm.matchTransform(local_space_group, display_mesh)
            pm.parent(display_mesh, local_space_group)
            pm.parent(local_space_group, display_radius_grp)

            pm.pointConstraint(light, local_space_group)
            pm.orientConstraint(light, local_space_group)

            local_space_group.translate.lock()
            local_space_group.rotate.lock()
            local_space_group.scale.lock()

            # Constraint
            radius_value = pm.getAttr(attr_radius)
            display_mesh.scaleZ.set(radius_value)
            pm.expression(n="%s_radiusScaleZ_displayRadius" % light.name() ,s="{MESH_NAME}.scaleZ = {LIGHT}".format(
                LIGHT=attr_radius,
                MESH_NAME=display_mesh.name()) )

            pm.expression(n="%s_radiusScaleX_displayRadius" % light.name() ,s="{MESH_NAME}.scaleX = {LIGHT}".format(
                LIGHT=attr_radius,
                MESH_NAME=display_mesh.name()) )

            pm.expression(n="%s_radiusScaleY_displayRadius" % light.name() ,s="{MESH_NAME}.scaleY = {LIGHT}".format(
                LIGHT=attr_radius,
                MESH_NAME=display_mesh.name()) )

            # lock mesh attribute dont needed
            pm.select(display_mesh)
            pm.transformLimits(esz=(True, False), sz=(0, 999999))
            display_mesh.rotate.lock()
            display_mesh.translate.lock()
            display_mesh.scaleX.lock()
            display_mesh.scaleY.lock()

            display_mesh.overrideEnabled.set(1)
            display_mesh.overrideDisplayType.set(2)

            out.append(light)

        if out:
            logger.info("Display Radius success" % ([lgt.name() for lgt in out]))
        else:
            logger.info("No 'aiRadius' display created")

        pm.select(save_selected)
        self.__displayRadiusCSS()
        return out

    @_wrapperUndoChunck
    def deleteDisplayRadius(self):
        """ Delete all 'aiRadius' display. """
        # Delete All expression
        pm.delete([expr for expr in pm.ls(typ="expression") if "displayRadius" in expr.name()])

        # Delete Folder
        if pm.objExists(self.display_radius_grp):
            pm.delete(self.display_radius_grp)

        # Delete light Utils if empty
        if pm.objExists(self.mtoa_utils_grp):
            if not pm.PyNode(self.mtoa_utils_grp).getChildren():
                pm.delete(self.mtoa_utils_grp)

        # Delete Shaders
        if pm.objExists("displayRadius_SHAD"):
            pm.delete("displayRadius_SHAD")

        if pm.objExists("displayRadius_SDEG"):
            pm.delete("displayRadius_SDEG")

        self.__displayRadiusCSS()
        logger.info("'aiRadius' display successfully deleted.")
        return True

    def __displayRadiusCSS(self):
        """ Stylize Display Radius button. """
        if pm.objExists(self.display_radius_grp):
            self.pushButton_displayRadius.setStyleSheet(self.css_btn_on)
        else:
            self.pushButton_displayRadius.setStyleSheet(self.css_btn_default)

    @_wrapperUndoChunck
    @_wrapperSelected
    def displayBlocker(self):
        """ Create 'aiLightBlocker' display from lights selected. """

        # Get Blockers
        blockers = []
        for sel in save_selected:
            if pm.nodeType(sel.name()) == "transform":
                if pm.nodeType(sel.getShape().name()) == "aiLightBlocker":
                    blockers.append(sel)

            else:
                if pm.nodeType(sel.name()) == "aiLightBlocker":
                    blockers.append(sel.getParent())

        # Abort if not blockers selected
        if not blockers:
            logger.warning("No Blockers found")
            return None

        # Rename all blockers
        for blocker in pm.ls(type="aiLightBlocker"):
            blocker_name = blocker.name()
            pm.rename(blocker.getParent(), "%s_C_001_AILB" % blocker_name)

        # Create mtoa utils grp
        utils_grp = self._eitherCreateGetNode("grp", self.mtoa_utils_grp)
        display_blocker_grp = self._eitherCreateGetNode("grp", self.display_blocker_grp)
        pm.parent(display_blocker_grp, utils_grp)

        # Create shader
        if not pm.objExists("displayBlocker_SHAD"):
            shader = pm.shadingNode("lambert", n="displayBlocker_SHAD", asShader=True)
            shading_group= pm.sets(renderable=True, n="displayBlocker_SDEG", noSurfaceShader=True, empty=True)
            pm.connectAttr('%s.outColor' % shader, '%s.surfaceShader' % shading_group)
            shader.color.set(0.8, 0.0, 0.2)
            shader.transparency.set(0.9, 0.9, 0.9)
            shader.translucence.set(1)
        else:
            shader = pm.PyNode("displayBlocker_SHAD")

        # Process
        out = []
        for blocker in blockers:
            #  query type of all blocker
            blocker_type = pm.getAttr("%s.geometryType" % blocker)
            display_mesh_name = re.sub(
                r"^(?P<lightname>[A-Za-z0-9]+)(?P<under>[_])(?P<utility>[a-zA-Z]*)(?P<left>[A-Za-z0-9_]+)$",
                r"\g<lightname>\g<under>displayBlocker\g<left>",
                blocker.name())

            if pm.objExists(display_mesh_name):
                continue

            # create Mesh
            if blocker_type == 0 :
                display_mesh = pm.polyCube(n=display_mesh_name)[0]

            elif blocker_type == 1 :
                display_mesh = pm.polySphere(r=0.5, sh=16, sa=16, n=display_mesh_name)[0]

            elif blocker_type == 2 :
                display_mesh = pm.polyCube( d=1, w=1, h=0.01, n=display_mesh_name)[0]
                pm.setAttr ( "%s.rx" %pm.ls(sl=True)[0], 90 )
                pm.makeIdentity ( pm.ls(sl=True)[0], apply=True, t=1, r=1, s=1, n=0, pn=1 )

            else :
                display_mesh = pm.polyCylinder(h=1, r=0, sa=16, n=display_mesh_name)[0]

            # Match Pivot
            piv_x, piv_y, piv_z, _, _, _ = pm.xform(blocker, q=True, piv=True)
            pm.xform(display_mesh, piv=(piv_x, piv_y, piv_z))

            # Assign shader
            pm.select(display_mesh)
            pm.hyperShade(assign=shader)

            # set attr
            display_mesh_shape = display_mesh.getShape()
            display_mesh_shape.attr("castsShadows").set(0)
            display_mesh_shape.attr("receiveShadows").set(0)
            display_mesh_shape.attr("motionBlur").set(0)
            display_mesh_shape.attr("primaryVisibility").set(0)
            display_mesh_shape.attr("smoothShading").set(0)
            display_mesh_shape.attr("visibleInReflections").set(0)
            display_mesh_shape.attr("visibleInRefractions").set(0)
            display_mesh_shape.attr("doubleSided").set(0)
            display_mesh_shape.attr("aiOpaque").set(0)
            display_mesh_shape.attr("aiVisibleInDiffuseReflection").set(0)
            display_mesh_shape.attr("aiVisibleInSpecularReflection").set(0)
            display_mesh_shape.attr("aiVisibleInDiffuseTransmission").set(0)
            display_mesh_shape.attr("aiVisibleInSpecularTransmission").set(0)
            display_mesh_shape.attr("aiSelfShadows").set(0)

            pm.parent(display_mesh, display_blocker_grp)

            pm.pointConstraint(blocker, display_mesh)
            pm.orientConstraint(blocker, display_mesh)
            pm.scaleConstraint(blocker, display_mesh)

            display_mesh.overrideEnabled.set(1)
            display_mesh.overrideDisplayType.set(2)

            out.append(display_mesh)

        if out:
            logger.info("Display Light Blocker success" % ([lgt.name() for lgt in out]))
        else:
            logger.info("No 'aiLightBlocker' display created")

        self.__displayBlockerCSS()
        return out

    def deleteDisplayBlocker(self):
        """ Delete all 'aiLightBlocker' display. """
        # Delete All expression
        pm.delete([expr for expr in pm.ls(typ="expression") if "displayBlocker" in expr.name()])

        # Delete Folder
        if pm.objExists(self.display_blocker_grp):
            pm.delete(self.display_blocker_grp)

        # Delete light Utils if empty
        if pm.objExists(self.mtoa_utils_grp):
            if not pm.PyNode(self.mtoa_utils_grp).getChildren():
                pm.delete(self.mtoa_utils_grp)

        # Delete Shaders
        if pm.objExists("displayBlocker_SHAD"):
            pm.delete("displayBlocker_SHAD")

        if pm.objExists("displayBlocker_SDEG"):
            pm.delete("displayBlocker_SDEG")

        self.__displayBlockerCSS()
        logger.info("'aiLightBlocker' display successfully deleted.")
        return True

    def __displayBlockerCSS(self):
        """ Stylize Display Blocker button. """
        if pm.objExists(self.display_blocker_grp):
            self.pushButton_displayBlocker.setStyleSheet(self.css_btn_on)
        else:
            self.pushButton_displayBlocker.setStyleSheet(self.css_btn_default)

    @_wrapperUndoChunck
    def displayDecay(self, decay_type):
        """ Create 'aiDecay' display from lights selected.

            Args:
                decay_type(str): type of decay that you want to display. 'near' or 'far'.
        """
        save_selected = pm.selected()
        # Init
        lights = self._onlyLightsFromSelection()
        if not lights:
            return

        # Create mtoa utils grp
        utils_grp = self._eitherCreateGetNode("grp", self.mtoa_utils_grp)
        display_decay_grp = None
        if decay_type == "near":
            display_decay_grp = self._eitherCreateGetNode("grp", self.display_decay_near_grp)
        elif decay_type == "far":
            display_decay_grp = self._eitherCreateGetNode("grp", self.display_decay_far_grp)

        pm.parent(display_decay_grp, utils_grp)

        # Create shader
        if not pm.objExists("displayDecayStart_SHAD"):
            shader_start = pm.shadingNode("lambert", n="displayDecayStart_SHAD", asShader=True)
            shading_group_start= pm.sets(renderable=True, n="displayDecayStart_SDEG", noSurfaceShader=True, empty=True)
            pm.connectAttr('%s.outColor' % shader_start, '%s.surfaceShader' % shading_group_start)
            shader_start.color.set(1.0, 0.7, 0.0)
            shader_start.transparency.set(0.9, 0.9, 0.9)
            shader_start.translucence.set(1)
        else:
            shader_start = pm.PyNode("displayDecayStart_SHAD")

        if not pm.objExists("displayDecayEnd_SHAD"):
            shader_end = pm.shadingNode("lambert", n="displayDecayEnd_SHAD", asShader=True)
            shading_group_end= pm.sets(renderable=True, n="displayDecayEnd_SDEG", noSurfaceShader=True, empty=True)
            pm.connectAttr('%s.outColor' % shader_end, '%s.surfaceShader' % shading_group_end)
            shader_end.color.set(1.00, 0.46, 0.00)
            shader_end.transparency.set(0.9, 0.9, 0.9)
            shader_end.translucence.set(1)
        else:
            shader_end = pm.PyNode("displayDecayEnd_SHAD")

        # Process
        pm.select(save_selected)
        out = []
        for light in lights:
            decay = light.getShape().inputs(type="aiLightDecay")

            # stop loop if decay doesn't exist
            if not decay:
                self.log.warning("No decay connected to %s" % light.name())
                continue

            # Get only one decay
            decay = decay[0]

            # Reloop if decay already exist
            if pm.PyNode("%s.%sEnd" % (decay, decay_type)).inputs(type="expression"):
                continue

            # Process
            for startEnd in ["Start", "End"]:
                attr_decay_name = decay_type + startEnd
                attr_decay_value = decay.attr(attr_decay_name).get()
                # Create Display Mesh
                display_mesh_name = re.sub(
                    r"^(?P<lightname>[A-Za-z0-9]+)(?P<under>[_])(?P<utility>[a-zA-Z]*)(?P<left>[A-Za-z0-9_]+)$",
                    r"\g<lightname>\g<under>display{}Decay\g<left>".format(startEnd),
                    light.name())

                if pm.nodeType(light.getShape().name()) == "spotLight":
                    display_mesh = pm.polyCylinder(sa=32, sc=0, height=0.01, n=display_mesh_name)[0]

                elif pm.nodeType(light.getShape().name()) == "pointLight":
                    display_mesh = pm.polySphere(n=display_mesh_name, subdivisionsAxis=36, subdivisionsHeight=36)[0]

                else:
                    display_mesh = pm.polyCube(n=display_mesh_name, height=0.01, width=2, depth=2)[0]

                # Assign Shader
                pm.select (display_mesh)
                pm.hyperShade(assign="displayDecay%s_SHAD" % startEnd)

                # Set no renderable
                display_mesh_shape = display_mesh.getShape()
                display_mesh_shape.attr("castsShadows").set(0)
                display_mesh_shape.attr("receiveShadows").set(0)
                display_mesh_shape.attr("motionBlur").set(0)
                display_mesh_shape.attr("primaryVisibility").set(0)
                display_mesh_shape.attr("smoothShading").set(0)
                display_mesh_shape.attr("visibleInReflections").set(0)
                display_mesh_shape.attr("visibleInRefractions").set(0)
                display_mesh_shape.attr("doubleSided").set(0)
                display_mesh_shape.attr("aiOpaque").set(0)
                display_mesh_shape.attr("aiVisibleInDiffuseReflection").set(0)
                display_mesh_shape.attr("aiVisibleInSpecularReflection").set(0)
                display_mesh_shape.attr("aiVisibleInDiffuseTransmission").set(0)
                display_mesh_shape.attr("aiVisibleInSpecularTransmission").set(0)
                display_mesh_shape.attr("aiSelfShadows").set(0)

                # Rotate
                display_mesh.rotateX.set(90)
                pm.select(display_mesh)
                pm.makeIdentity(apply=True, t=1, r=1, s=1, n=0, pn=1)
                display_mesh.rotateOrder.set(2)

                # Align mesh to light
                pm.pointConstraint(light, display_mesh)
                pm.pointConstraint(light, display_mesh, rm=True)
                pm.orientConstraint(light, display_mesh)
                pm.orientConstraint(light, display_mesh, rm=True)

                # Create new local space
                local_space_name = re.sub(
                    r"^(?P<lightname>[A-Za-z0-9]+)(?P<under>[_])(?P<utility>[a-zA-Z]*)(?P<left>[A-Za-z0-9_]+)$",
                    r"\g<lightname>\g<under>localSpace{}Decay\g<left>".format(startEnd),
                    light.name())

                local_space_group = pm.group(em=True, n=local_space_name)
                pm.matchTransform(local_space_group, display_mesh)
                pm.parent(display_mesh, local_space_group)
                pm.parent(local_space_group, display_decay_grp)

                pm.pointConstraint(light, local_space_group)
                pm.orientConstraint(light, local_space_group)

                local_space_group.translate.lock()
                local_space_group.rotate.lock()
                local_space_group.scale.lock()
                # Get angle

                # Constraint
                if pm.nodeType(light.getShape().name()) == "spotLight":
                    cone_angle = light.coneAngle.get()
                    display_mesh.translateZ.set(-(attr_decay_value))
                    pm.expression(n="%s_%s_decayTranslateZ_displayDecay" % (light.name(), startEnd) ,s="{DECAY_NAME}.{DECAY_TYPE} = -({MESH_NAME}.translateZ)".format(
                        DECAY_NAME=decay.name(),
                        DECAY_TYPE=attr_decay_name,
                        MESH_NAME=display_mesh.name())
                    )
                    # lock attribute of mesh dont needed
                    pm.select(display_mesh)
                    pm.transformLimits(etz=(False, True), tz=(-10000, 0))
                    display_mesh.rotate.lock()
                    #display_mesh.scale.lock()
                    display_mesh.translateX.lock()
                    display_mesh.translateY.lock()

                elif pm.nodeType(light.getShape().name()) == "pointLight":
                    display_mesh.scaleZ.set(attr_decay_value)
                    pm.expression(n="%s_%s_decayScaleZ_displayDecay" % (light.name(), startEnd) ,s="{DECAY_NAME}.{DECAY_TYPE} = ({MESH_NAME}.scaleZ)".format(
                        DECAY_NAME=decay.name(),
                        DECAY_TYPE=attr_decay_name,
                        MESH_NAME=display_mesh.name())
                    )
                    pm.expression(n="%s_%s_decayScaleX_displayDecay" % (light.name(), startEnd) ,s="{MESH_NAME}.scaleX = ({MESH_NAME}.scaleZ)".format(
                        MESH_NAME=display_mesh.name())
                    )
                    pm.expression(n="%s_%s_decayScaleY_displayDecay" % (light.name(), startEnd) ,s="{MESH_NAME}.scaleY = ({MESH_NAME}.scaleZ)".format(
                        MESH_NAME=display_mesh.name())
                    )
                    # lock attribute of mesh dont needed
                    pm.select(display_mesh)
                    pm.transformLimits(esz=(True, False), sz=(0, 999999))
                    display_mesh.rotate.lock()
                    display_mesh.translate.lock()
                    display_mesh.scaleX.lock()
                    display_mesh.scaleY.lock()

                else:
                    display_mesh.translateZ.set(-(attr_decay_value))
                    pm.expression(n="%s_%s_decayTranslateZ_displayDecay" % (light.name(), startEnd) ,s="{DECAY_NAME}.{DECAY_TYPE} = -({MESH_NAME}.translateZ)".format(
                        DECAY_NAME=decay.name(),
                        DECAY_TYPE=attr_decay_name,
                        MESH_NAME=display_mesh.name())
                    )
                    pm.expression(n="%s_%s_decayTranslateZ_displayDecay" % (light.name(), startEnd) ,s="{DECAY_NAME}.{DECAY_TYPE} = -({MESH_NAME}.translateZ)".format(
                        DECAY_NAME=decay.name(),
                        DECAY_TYPE=attr_decay_name,
                        MESH_NAME=display_mesh.name())
                    )
                    # lock attribute of mesh dont needed
                    pm.select(display_mesh)
                    pm.transformLimits(etz=(False, True), tz=(-10000, 0))
                    display_mesh.rotate.lock()
                    #display_mesh.scale.lock()
                    display_mesh.translateX.lock()
                    display_mesh.translateY.lock()


            # Set Decay ON
            use_decay = "use%sAtten" % decay_type.capitalize()
            decay.attr(use_decay).set(1)
            out.append(light)

        if out:
            logger.info("Display Decay success" % ([lgt.name() for lgt in out]))
        else:
            logger.info("No 'aiDecay' display created")

        self.__displayDecayCSS()
        return out

    def deleteDisplayDecay(self):
        """ Delete all 'aiDecay' display. """
        # Delete All expression
        pm.delete([expr for expr in pm.ls(typ="expression") if "displayDecay" in expr.name()])

        # Delete Folder
        if pm.objExists(self.display_decay_far_grp):
            pm.delete(self.display_decay_far_grp)

        # Delete Folder
        if pm.objExists(self.display_decay_near_grp):
            pm.delete(self.display_decay_near_grp)

        # Delete light Utils if empty
        if pm.objExists(self.mtoa_utils_grp):
            if not pm.PyNode(self.mtoa_utils_grp).getChildren():
                pm.delete(self.mtoa_utils_grp)

        # Delete Shaders
        if pm.objExists("displayDecayStart_SHAD"):
            pm.delete("displayDecayStart_SHAD")

        if pm.objExists("displayDecayEnd_SHAD"):
            pm.delete("displayDecayEnd_SHAD")

        if pm.objExists("startDisplayDecay_SDEG"):
            pm.delete("startDisplayDecay_SDEG")

        if pm.objExists("endDisplayDecay_SDEG"):
            pm.delete("endDisplayDecay_SDEG")

        self.__displayDecayCSS()
        logger.info("'aiDecay' display successfully deleted.")
        return

    def __displayDecayCSS(self):
        """ Stylize Display Decay button. """
        if pm.objExists(self.display_decay_near_grp):
            self.pushButton_displayNearDecay.setStyleSheet(self.css_btn_on)
        else:
            self.pushButton_displayNearDecay.setStyleSheet(self.css_btn_default)

        if pm.objExists(self.display_decay_far_grp):
            self.pushButton_displayFarDecay.setStyleSheet(self.css_btn_on)
        else:
            self.pushButton_displayFarDecay.setStyleSheet(self.css_btn_default)

    def advancedSelection(self):
        """ Advanced selection. """
        # Get infos
        name_ = str(self.lineEdit_advancedSelection_name.text())
        type_ = str(self.lineEdit_advancedSelection_type.text())

        # Shift string to list
        names_ = [n for n in re.split(r",([ ]?)+", name_) if n]
        types_ = [n for n in re.split(r",([ ]?)+", type_) if n]

        if not names_ and not types_:
            logger.warning("No 'name' and 'type' found.")
            return None

        if self.radioButton_advancedSelection_root.isChecked() and self.radioButton_advancedSelection_exclude.isChecked():
            logger.warning("'Exclude mode' is disabled with 'root mode'")
            return None

        # Make list
        out_shapes = None
        if types_ and names_:
            out_shapes = pm.ls(names_, typ=types_, dag=True)

        elif types_ and not names_:
            out_shapes = pm.ls(typ=types_, dag=True)

        elif names_ and not types_:
            out_shapes = pm.ls(names_, dag=True)

        # If selected
        selected_children = []
        if self.radioButton_advancedSelection_selected.isChecked():
            selected = pm.selected()
            if not selected:
                logger.warning("Nothing selected in scene")
                return None

            # Populate list
            for sel_ in selected:
                selected_children.extend([shape for shape in sel_.getChildren(ad=True, s=True) if pm.nodeType(shape.name()) != "srHookShape"])

            # Include/Exclude process
            if self.radioButton_advancedSelection_exclude.isChecked():
                out_shapes = list(set(selected_children).difference(out_shapes))
            else:
                out_shapes = list(set(selected_children).intersection(out_shapes))

        # Get transform from lists
        out_transforms = [shape.getParent() for shape in out_shapes]

        # Return if list is empty
        if not out_transforms:
            logger.warning("Something is wrong, Nothing to selected")
            return None

        return_name = [node.name() for node in out_transforms]
        logger.info("adavanced selection : %s" % return_name)
        pm.select(out_transforms)

    def colorOutlinerSelected(self, color_, enable=True):
        """ Colorize Item selected in outliner. """
        # PREPROCESS
        selected = pm.selected()
        set_color = None
        if color_ == "red":
            set_color = (1.000, 0.500, 0.500)

        elif color_ == "orange":
            set_color = (0.900, 0.700, 0.400)

        elif color_ == "yellow":
            set_color = (1.000, 1.000, 0.500)

        elif color_ == "green":
            set_color = (0.600, 1.000, 0.400)

        elif color_ == "turquoise":
            set_color = (0.300, 1.000, 0.700)

        elif color_ == "cyan":
            set_color = (0.500, 1.000, 1.000)

        elif color_ == "blue":
            set_color = (0.300, 0.700, 1.000)

        elif color_ == "purple":
            set_color = (0.600, 0.400, 1.000)

        elif color_ == "magenta":
            set_color = (1.000, 0.500, 1.000)

        else:
            set_color = (0.000, 0.000, 0.000)

        # Return if selection is empty
        if not selected:
            logger.warning("Nothing selected")
            return

        # Remove Color outliner
        if not enable:
            for node in selected:
                node.useOutlinerColor.set(False)
            logger.info("Color Outliner disabled")
            pm.mel.eval("AEdagNodeCommonRefreshOutliners()")
            return

        # Set Color outliner
        for node in selected:
            node.useOutlinerColor.set(True)
            node.outlinerColor.set(set_color)

        pm.mel.eval("AEdagNodeCommonRefreshOutliners()")
        logger.info("Color Outliner success")

    def selectChildren(self):
        """ Select All tranforms children from selection """
        include = self.lgt_types + ["mesh"]
        selected = pm.selected()

        # Return if selection is empty
        if not selected:
            logger.warning("Nothing selected")
            return None

        # Get shapes
        out_shapes = []
        for node in selected:
            out_shapes.extend([node for node in node.getChildren(ad=True, s=True)])
            if pm.nodeType(node.name()) in include:
                out_shapes.append(node)

        # Get transform node
        out_transforms = [shape.getParent() for shape in out_shapes]

        pm.select(out_transforms)
        logger.info("%s selected" % [node.name() for node in out_transforms])
        return out_transforms

    def getUnusedLightFilters(self, ai_filter):
        """ Get light filters disconnected from all and light filters with null value.

            Args:
                ai_filter(str): filter that you want to delete. 'aiLightDecay' or 'aiLightBlocker'.

            Returns:
                (dict) Disconnect and null light filters.
        """
        # Check input attributes
        if ai_filter not in ["aiLightDecay", "aiLightBlocker"]:
            logger.error("'aiLightDecay' or 'aiLightBlocker'")
            return None

        # Get filters
        all_lightfilters = pm.ls(type=ai_filter)
        if not all_lightfilters:
            logger.warning("No %s found" % ai_filter)
            return None

        # Get disconnected filters
        disconnected_filters = []
        connected_filters = []
        for lightfilter in all_lightfilters:
            if not lightfilter.outputs():
                disconnected_filters.append(lightfilter)
            else:
                connected_filters.append(lightfilter)

        # Get filters with null value
        null_filters = []
        if ai_filter == "aiLightBlocker":
            for blocker in connected_filters:
                if not blocker.density.get():
                    null_filters.append(blocker)

        if ai_filter == "aiLightDecay":
            for decay in connected_filters:
                if not decay.useNearAtten.get() and not decay.useFarAtten.get():
                    null_filters.append(decay)


        if not disconnected_filters and not null_filters:
            logger.info("All filters is used.")
            return None

        else:
            return {"disconnected" : disconnected_filters, "null" : null_filters, "type" : ai_filter}

    @_wrapperUndoChunck
    def deleteSafelyLightFilter(self, ai_filter):
        """ Delete safely unused Arnold light filter.

            Args:
                ai_filter(str): filter that you want to delete. 'aiLightDecay' or 'aiLightBlocker'
        """
        # Check input attributes
        if ai_filter not in ["aiLightDecay", "aiLightBlocker"]:
            logger.error("'aiLightDecay' or 'aiLightBlocker'")
            return None

        # Get unused light filters
        lightfilters = self.getUnusedLightFilters(ai_filter)
        if lightfilters is None:
            return None

        # Sort lightfilters
        #FLTR_WINDOW = JMUnusedLightFiltersUI(lightfilters)
        #sorted_lightfilters = FLTR_WINDOW.filters_to_delete

        # Disconnect null filters from light
        for lightfilter in lightfilters["null"]:
            # Get connected lights
            lights = pm.connectionInfo("%s.message" % lightfilter, dfs=True)
            lights = [connection for connection in lights if "aiFilters" in connection]

            for light in lights :
                light_node = pm.PyNode(light.split(".")[0])
                num_filter = len( pm.PyNode("%s.aiFilters" % light_node).inputs() )
                index = int( re.findall(r"\[[0-9]+\]", light)[0].strip("[]") )

                i = 0
                while (i < num_filter):
                    if i == index:
                        pm.PyNode("%s.message" % lightfilter) // pm.PyNode(pm.PyNode("%s.aiFilters[%s]" % (light_node, i)))

                    if i > index:
                        other_filter = pm.connectionInfo("%s.aiFilters[%s]" % (light_node, i), sfd=True)
                        other_filter = pm.PyNode(other_filter)
                        other_filter // pm.PyNode("%s.aiFilters[%s]" % (light_node, i))
                        other_filter >> pm.PyNode("%s.aiFilters[%s]" % (light_node, i - 1))

                    i += 1

        # Delete unused and null filters
        deleted_filters = lightfilters["disconnected"] + lightfilters["null"]
        for lightfilter in deleted_filters:
            if pm.objExists(lightfilter):
                try:
                    pm.delete(lightfilter.getParent())
                except AttributeError :
                    pm.delete(lightfilter)

        logger.info("Safely deleted {0} : {1}".format(ai_filter, deleted_filters))
        return deleted_filters

    def __listUnusedLightFiltersUI(self, ai_filter):
        """ List Unused light filters in UI.

            Args:
                ai_filter(str): filter that you want to delete. 'aiLightDecay' or 'aiLightBlocker'
        """
        # Get unused light filters
        lightfilters = self.getUnusedLightFilters(ai_filter)
        if lightfilters is None:
            return None

        # Delete UI
        if pm.window("jmUnusedLightFilters", exists=True):
            pm.deleteUI("jmUnusedLightFilters")

        pm.window("jmUnusedLightFilters", t="Unused light filters", w=250, h=400, s=False)
        pm.columnLayout(adj=True)
        #list_view_disconnected = pm.textScrollList("scroll",
        #    allowMultiSelection=True,
        #    append=lightfilters["disconnected"],
        #    height=300,
        #    selectIndexedItem=True )
        #    #selectCommand=connectSlider )

        list_view_null = pm.textScrollList("scroll",
            allowMultiSelection=True,
            append=lightfilters["null"],
            height=300,
            selectIndexedItem=True )
            #selectCommand=connectSlider )

        popup = pm.popupMenu(parent=list_view, ctl=False, button=3)
        #pm.menuItem(i="refresh.png", l='Reload list', c=reloadList)
        #pm.menuItem("check", label="ignore safelocked node", checkBox=False, c=connectSlider )

        pm.columnLayout(adj=True)

        #connectSlider()
        pm.showWindow()

    def selectNotIlluminatingLights(self):
        """ Select not Illuminating lights """
        not_illuminating = []
        for light in self._getAllLights():
            if not pm.lightlink(light=light):
                not_illuminating.append(light)

        if not not_illuminating:
            logger.info("all Lights is linked")
            return

        pm.select(not_illuminating)
        logger.info("%s illuminate nothing" % [lgt.name() for lgt in not_illuminating])

    def lightOptimizer__selectLightsFromList(self):
        """ Select lights from 'lightOptimizer' item selected. """
        # Get lightname from list
        lights = []
        for item in self.listWidget_lightOptimizer.selectedItems():
            datas = item.data(CUSTOM_IDX)
            lights.append(pm.PyNode(datas["lightname"]))

        # Get transform
        lights_transform = [node.getParent() for node in lights]
        pm.select(lights_transform)

        return_lgts_name = [lgts.name() for lgts in lights_transform]
        logger.info("Select : %s" % return_lgts_name)

    def lightOptimizer__setMultiplesValues(self):
        """ Set multiples values from 'lightOptimizer' item selected. """
        value = self.doubleSpinBox_lightOptimizer_value.value()
        lights = []

        for item in self.listWidget_lightOptimizer.selectedItems():
            datas = item.data(CUSTOM_IDX)
            light_node = pm.PyNode("%s.%s" % (datas["lightname"], datas["attribute"]))
            lights.append(light_node)

        for light in lights:
            light.set(value)

        logger.info("lights : %s, value : %s" % (lights, value))

    def _lightOptimizer__sortingLights(self, attr_):
        """ Sort lights attributes values.

            Args:
                attr_ (str): Attribute.

            Returns;
                (list) : lights data.
        """
        # Get UI values
        self.listWidget_lightOptimizer.clear()
        min_value = self.spinBox_lightOptimizer_min.value()
        max_value = self.spinBox_lightOptimizer_max.value()
        attr_ = str(self.comboBox_lightOptimizer_attributes.currentText())

        # Get all lights
        all_lights = self._getAllLights(get_shapes=True)
        if all_lights is None:
            return None

        out = []
        for light in all_lights:
            value = pm.getAttr("%s.%s" % (light, attr_))

            if (value >= min_value) and (value <= max_value):
                light_data = {
                    "lightname" : light.name(),
                    "transform" : light.getParent().name(),
                    "type" : pm.nodeType(light.name()),
                    "attribute" : attr_,
                    "value" : value }

                out.append(light_data)

            elif (max_value == 11) and (value >= 10) and (attr_ in ["aiSamples", "aiVolumeSamples"]):
                light_data = {
                    "lightname" : light.name(),
                    "transform" : light.getParent().name(),
                    "type" : pm.nodeType(light.name()),
                    "attribute" : attr_,
                    "value" : value }

            elif (max_value == 101) and (value >= 100) and (attr_ == "aiRadius"):
                light_data = {
                    "lightname" : light.name(),
                    "transform" : light.getParent().name(),
                    "type" : pm.nodeType(light.name()),
                    "attribute" : attr_,
                    "value" : value }

            elif (max_value == 21) and (value >= 20) and (attr_ in ["aiExposure", "intensity"]):
                light_data = {
                    "lightname" : light.name(),
                    "transform" : light.getParent().name(),
                    "type" : pm.nodeType(light.name()),
                    "attribute" : attr_,
                    "value" : value }

                out.append(light_data)

        reordered_list = reversed(sorted(out, key=lambda k: k['value']))
        return reordered_list

    def __lightOptimizer__populateGrid(self):
        """ Populate 'lightOptimizer' grid from light attributes. """
        # Get UI values and sorted lights
        attr_ = str(self.comboBox_lightOptimizer_attributes.currentText())
        lights = self._lightOptimizer__sortingLights(attr_)

        # Return if no lights
        if lights is None:
            return None

        for item in lights:
            item_ui = JMLightOptimizerItem(item, self.__lightOptimizer__populateGrid)

            list_widget_item = QtWidgets.QListWidgetItem()
            list_widget_item.setSizeHint(item_ui.sizeHint())
            list_widget_item.setData(CUSTOM_IDX, item)

            self.listWidget_lightOptimizer.addItem(list_widget_item)
            self.listWidget_lightOptimizer.setItemWidget(list_widget_item, item_ui)

        return lights

    def __lightOptimizer__populateComboBox(self):
        """ Populate 'lightOptimizer' combo box attributes. """
        for attr in self.optimize_attrs:
            self.comboBox_lightOptimizer_attributes.addItem(self.icon_blank, attr)

    def __lightOptimizer__adaptSlider(self):
        """ Adapting slider value per attributes. """
        current_text = self.comboBox_lightOptimizer_attributes.currentText()
        if current_text in ["aiSamples", "aiVolumeSamples"]:
            self.horizontalSlider_lightOptimizer_min.setMaximum(11)
            self.spinBox_lightOptimizer_min.setMaximum(11)
            self.horizontalSlider_lightOptimizer_max.setMaximum(11)
            self.spinBox_lightOptimizer_max.setMaximum(11)

        elif current_text in ["aiIndirect", "aiVolume"]:
            self.horizontalSlider_lightOptimizer_min.setMaximum(1)
            self.spinBox_lightOptimizer_min.setMaximum(1)
            self.horizontalSlider_lightOptimizer_max.setMaximum(1)
            self.spinBox_lightOptimizer_max.setMaximum(1)

        elif current_text == "aiMaxBounces":
            self.horizontalSlider_lightOptimizer_min.setMaximum(999)
            self.spinBox_lightOptimizer_min.setMaximum(999)
            self.horizontalSlider_lightOptimizer_max.setMaximum(999)
            self.spinBox_lightOptimizer_max.setMaximum(999)

        elif current_text == "aiRadius":
            self.horizontalSlider_lightOptimizer_min.setMaximum(101)
            self.spinBox_lightOptimizer_min.setMaximum(101)
            self.horizontalSlider_lightOptimizer_max.setMaximum(101)
            self.spinBox_lightOptimizer_max.setMaximum(101)

        elif current_text in ["aiExposure", "intensity"]:
            self.horizontalSlider_lightOptimizer_min.setMaximum(21)
            self.spinBox_lightOptimizer_min.setMaximum(21)
            self.horizontalSlider_lightOptimizer_max.setMaximum(21)
            self.spinBox_lightOptimizer_max.setMaximum(21)

        else:
            logger.error("Out Range.")

    def __lightOptimizer__toggleSync(self):
        """ Connect 'lightOptimizer' UI if button is checked. """
        if pm.pluginInfo("mtoa", q=True, loaded=True):
            if self.pushButton_lightOptimizer_sync.isChecked():
                self.pushButton_lightOptimizer_sync.setStyleSheet(self.default_stylesheet)
                self.pushButton_lightOptimizer_sync.setIcon(self.icon_sync_on)

                self.comboBox_lightOptimizer_attributes.currentIndexChanged.connect(self.__lightOptimizer__populateGrid)
                self.comboBox_lightOptimizer_attributes.currentIndexChanged.connect(self.__lightOptimizer__adaptSlider)
                self.horizontalSlider_lightOptimizer_min.valueChanged.connect(self.__lightOptimizer__populateGrid)
                self.horizontalSlider_lightOptimizer_max.valueChanged.connect(self.__lightOptimizer__populateGrid)
                self.pushButton_lightOptimizer_setValue.clicked.connect(self.__lightOptimizer__populateGrid)
                self.__lightOptimizer__populateGrid()

            else:
                    self.pushButton_lightOptimizer_sync.setStyleSheet(self.default_stylesheet)
                    self.pushButton_lightOptimizer_sync.setIcon(self.icon_sync_off)

                    try:
                        self.comboBox_lightOptimizer_attributes.currentIndexChanged.disconnect(self.__lightOptimizer__populateGrid)
                        self.comboBox_lightOptimizer_attributes.currentIndexChanged.disconnect(self.__lightOptimizer__adaptSlider)
                        self.horizontalSlider_lightOptimizer_min.valueChanged.disconnect(self.__lightOptimizer__populateGrid)
                        self.horizontalSlider_lightOptimizer_max.valueChanged.disconnect(self.__lightOptimizer__populateGrid)
                        self.pushButton_lightOptimizer_setValue.clicked.disconnect(self.__lightOptimizer__populateGrid)
                    except RuntimeError:
                        pass

                    self.listWidget_lightOptimizer.clear()

        else:
            pm.confirmDialog(title=__name__, icn="warning", message="'lightOptimizer' was designed for MtoA.", button=['OK'])

    def _getAllLights(self, get_shapes=False):
        """ Get all standard/Arnold lights from scene.

            Args:
                get_shapes (bool): Return 'shape' if True, otherwrise return 'transform'.

            Returns:
                (list): All lights from scene
        """
        lights = []
        for lgt_type in self.lgt_types:
            lights.extend(pm.ls(type=lgt_type))

        # Return if list is empty
        if not lights:
            logger.warning("No lights in scene")
            return None

        # Get Transform if not 'get_shapes'
        if not get_shapes:
            lights = [shape.getParent() for shape in lights]

        logger.debug("_getAllLights : %s" % lights)
        return lights

    def _onlyLightsFromSelection(self, get_shapes=False, all_hierachy=False):
        """ Isolate Lights From Selection.

            Args:
                get_shapes (bool): Return 'shape' if True, otherwrise return 'transform'.
                all_hierachy (bool): Get all selection children if True.

            Returns:
                (list): Selected lights
        """
        # Get either selection or selection + children
        selection = []
        if all_hierachy:
            for node in pm.selected():
                children = [nde for nde in node.getChildren(ad=True) if pm.nodeType(nde.name()) != "transform"]
                selection.extend(children)
        else:
            selection.extend(pm.selected())

        lights = []
        for node in selection:
            # Get shape
            if pm.nodeType(node.name()) == "transform":
                node = node.getShape()
                if node is None:
                    continue

            # Check node type then append it to 'lights' list if is a light node
            if pm.nodeType(node.name()) in self.lgt_types:
                lights.append(node)

        # Return if list is empty
        if not lights:
            logger.warning("No lights selected")
            return None

        # Get Transform if not 'get_shapes'
        if not get_shapes:
            lights = [shape.getParent() for shape in lights]

        logger.debug("_onlyLightsFromSelection : %s" % lights)
        return lights

    def _eitherCreateGetNode(self, node_type, node_name):
        """ Either create or get existing node.

            Args:
                node_type (str): Node type to either get or create.
                node_name (str): Node name to either get or create.

            Returns:
                (PyNode): Node either getted or created.
        """
        node = None
        if pm.objExists(node_name):
            node = pm.PyNode(node_name)
        else:
            if node_type == "grp":
                node = pm.group(em=True, n=node_name)
            else:
                node = pm.createNode(node_type, n=node_name, ss=True)

        return node


class JMLookThroughWindow(MayaQWidgetDockableMixin, QtWidgets.QWidget):
    """ Create Look through window. """
    def __init__(self):
        """ Initialize JMLookThroughWindow. """
        super(JMLookThroughWindow, self).__init__(parent=None)
        self.setWindowFlags(QtCore.Qt.Tool)
        self.setWindowTitle("JMLookThroughWindow")
        self.setObjectName("JMLookThroughWindow")

        self.starting_size = QtCore.QSize(300, 300)
        self.minimum_size = QtCore.QSize(100, 100)
        self.preferredSize = self.starting_size
        self.resize(self.preferredSize)
        self.panel = None

        self.deleteLookedThroughCam()

        # Create Panel layout
        layout = QtWidgets.QVBoxLayout()
        layout.setObjectName(self.objectName() + "VerticalBoxLayout")
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(8)

        btn = QtWidgets.QPushButton()
        btn.setText("Select Light")
        btn.setMinimumHeight(35)
        btn.clicked.connect(self.selectLight)
        layout.addWidget(btn)

        self.setLayout(layout)

        # Get layout name
        layout_name = omui.MQtUtil.fullName(long(getCppPointer(layout)[0]))
        old_parent = pm.setParent(query=True)
        pm.cmds.setParent(layout_name)

        # Either create or get panel
        panel_name = self.objectName() + "ModelPanelLabel"
        previous_panel = pm.cmds.getPanel(withLabel=panel_name)
        self.panel = pm.cmds.modelPanel()
        pm.cmds.modelPanel(self.panel, edit=True, label=panel_name, parent=layout)

        # Delete previous panel
        if previous_panel is not None:
            pm.deleteUI(previous_panel, panel=True)

        # Edit panel
        editor = pm.cmds.modelPanel(self.panel, query=True, modelEditor=True)
        pm.cmds.modelEditor(editor, edit=True, displayAppearance="smoothShaded", locators=True)

        # Set Parent
        pm.cmds.setParent(old_parent)

    def dockCloseEventTriggered(self):
        global LOOK_WINDOW
        LOOK_WINDOW = None
        self.deleteLookedThroughCam()

    def deleteLookedThroughCam(self):
        """ Delete Camera created by looktrough """
        looked_through = MAIN_WINDOW._isLookThrough()
        if looked_through is not None:
            pm.delete(looked_through)

    def selectLight(self):
        """ Select light from look through window """
        pm.select(self.lightname)

    def lookThroughLightSelected(self):
        self.lightname = None
        selected = MAIN_WINDOW._onlyLightsFromSelection()
        if selected:
            self.lightname = selected[-1].name()

        if self.lightname and self.panel:
            self.setWindowTitle(self.lightname)
            cmd = "lookThroughModelPanelClipped(\"" + self.lightname + "\", \"" + self.panel + "\", 0.001, 1000)"
            pm.mel.eval(cmd)
            logger.info("Look through : %s" % self.lightname)

            if pm.objExists("cameraShape1"):
                pm.setAttr("cameraShape1.farClipPlane", 1000000)
                pm.setAttr("cameraShape1.nearClipPlane", 0.001)

        else:
            self.setWindowTitle("NO LIGHT")


class JMLightOptimizerItem(QtWidgets.QWidget, Ui_widget_unusedFiltersItem):
    """ Custom 'LightOptimizer' widget appended to UI. """
    def __init__(self, datas, populateFunction):
        """ Initialize JMLightOptimizerItem. """
        super(JMLightOptimizerItem, self).__init__()
        self.setupUi(self)
        self.populate_parent = populateFunction
        self.label_lightname.setText(datas["transform"])
        self.label_attribute.setText("%s :" % datas["attribute"])
        self.doubleSpinBox_attributeValue.setValue(datas["value"])

        # Attributes
        self.lightname = datas["lightname"]
        self.attribute = datas["attribute"]
        self.light_type = datas["type"]
        self.current_value = datas["value"]
        self.node = pm.PyNode(self.lightname)
        self.transform_node = self.node.getParent()

        # Stylize button
        button_CSS = "QPushButton{border-radius:20px; background-color: #5d5d5d; border:5px #14E696;} "
        button_hover_CSS = "QPushButton:hover{border-radius:20px; background-color: #949494; border:5px #14E696;} "
        self.pushButton_Icon.setStyleSheet(button_CSS + button_hover_CSS)

        light_icon = QtGui.QIcon(os.path.join(PROJECT_DIR, "resources", "icons", "%s.svg" % self.light_type))
        self.pushButton_Icon.setIcon(light_icon)

        # Connect Methods to UI
        self.pushButton_Icon.clicked.connect(self.selectLight)
        self.pushButton_setValue.clicked.connect(self.setValue)

    def selectLight(self):
        """ Select light. """
        pm.select(self.transform_node)
        logger.info("select : %s" % self.transform_node)

    def setValue(self):
        """ Set new value attribute. """
        value = self.doubleSpinBox_attributeValue.value()
        pm.setAttr("%s.%s" % (self.lightname, self.attribute), value)

        self.populate_parent()
        logger.info("value : {0}, attribute : {1}, light : {2}".format(value, self.attribute, self.lightname))


class JMUnusedLightFiltersUI(MayaQWidgetDockableMixin, QtWidgets.QWidget, Ui_widget_unusedFiltersList):
    """ Unused light filters UI. """
    def __init__(self, lightfilters, parent=None):
        """ Initialize JMUnusedLightFiltersUI """
        super(JMUnusedLightFiltersUI, self).__init__(parent=parent)
        self.setWindowFlags(QtCore.Qt.Tool)
        self.setupUi(self)
        self.setWindowTitle(__name__ + "- Unused lights filters")
        self.setObjectName(__name__ + "LightFilters")

        # Attributes
        self.filter_type = lightfilters["type"]
        self.disconnected_filters = lightfilters["disconnected"]
        self.null_filters = lightfilters["null"]
        self.label_disconnectedFilters.setText("Disconnected %s :" % self.filter_type)
        self.label_nullFilters.setText("Null %s :" % self.filter_type)
        self.filters_to_delete = { "disconnected" : [], "null" : [] }

        # Connect Methods to UI
        self.pushButton_delete.clicked.connect(self.getFilterSelected)
        self.pushButton_delete.clicked.connect(self.deleteLater)
        self.pushButton_cancel.clicked.connect(self.deleteLater)

        # Pre-build Methods
        self.__populateList()
        self.show()

    def getFilterSelected(self):
        """ Get lighfilters name from selected items. """
        for item in self.listWidget_disconnectedFilters.selectedItems():
            filter_name = item.data(CUSTOM_IDX)
            self.filters_to_delete["disconnected"].append(filter_name)

        for item in self.listWidget_nullFilters.selectedItems():
            filter_name = item.data(CUSTOM_IDX)
            self.filters_to_delete["null"].append(filter_name)

    def __populateList(self):
        """ Populate 'Disconnected' and 'Null' list widget. """
        # Check list
        if not self.disconnected_filters and not self.null_filters:
            return None

        # Populate Disconnect filters
        if self.disconnected_filters:
            for filter in self.disconnected_filters:
                item_ui = JMUnusedLightFiltersItem(filter.name())

                list_widget_item = QtWidgets.QListWidgetItem()
                list_widget_item.setSizeHint(item_ui.sizeHint())
                list_widget_item.setData(CUSTOM_IDX, filter.name())

                self.listWidget_disconnectedFilters.addItem(list_widget_item)
                self.listWidget_disconnectedFilters.setItemWidget(list_widget_item, item_ui)

        if self.null_filters:
            for filter in self.null_filters:
                item_ui = JMUnusedLightFiltersItem(filter.name())

                list_widget_item = QtWidgets.QListWidgetItem()
                list_widget_item.setSizeHint(item_ui.sizeHint())
                list_widget_item.setData(CUSTOM_IDX, filter.name())

                self.listWidget_nullFilters.addItem(list_widget_item)
                self.listWidget_nullFilters.setItemWidget(list_widget_item, item_ui)

        return self.disconnected_filters + self.null_filters


class JMUnusedLightFiltersItem(QtWidgets.QWidget, Ui_widget_unusedFiltersItem):
    """ List disconnected and null light filters in list. """
    def __init__(self, filter_name):
        """ Initialize JMUnusedLightFiltersItem. """
        super(JMUnusedLightFiltersItem, self).__init__()
        self.setupUi(self)
        self.filter_name = filter_name

        self.label_filterName.setText(self.filter_name)
        select_icon = QtGui.QIcon(os.path.join(PROJECT_DIR, "resources", "icons", "icon_select2.png"))
        self.pushButton_select.setIcon(select_icon)
        self.pushButton_select.clicked.connect(self.selectFilter)

    def selectFilter(self):
        """ Select light filter from item. """
        pm.select(self.filter_name )
        logger.info("select : %s" % self.filter_name )


def promptDialogMtoA():
    """ Prompt a dialog and ask if you want load MtoA. """
    if not pm.pluginInfo("mtoa", q=True, loaded=True):
        message = "MtoA is not loaded, do you want to load it?"
        status = pm.confirmDialog(title=__name__, message=message, button=['Yes', 'No'],
            defaultButton='Yes', cancelButton='No', dismissString='No')

        if status == "Yes":
            try:
                pm.loadPlugin("mtoa")
            except RuntimeError,e:
                logger.warning(e)

def _lookThroughWindowClosed():
    """ Close Callback lookthrough UI. """
    global LOOK_WINDOW
    if LOOK_WINDOW:
        LOOK_WINDOW.deleteLookedThroughCam()
        LOOK_WINDOW = None

def createLookThroughWindow(restore=False):
    """ Run LookThrough UI. """
    global LOOK_WINDOW

    if MAIN_WINDOW is None:
        return

    if not MAIN_WINDOW._onlyLightsFromSelection():
        return

    control = "JMLookThroughWindow" + "WorkspaceControl"
    if pm.workspaceControl(control, q=True, exists=True) and LOOK_WINDOW is None:
        pm.workspaceControl(control, e=True, close=True)
        pm.deleteUI(control)

    if restore:
        restored_control = omui.MQtUtil.getCurrentParent()

    if LOOK_WINDOW is None:
        LOOK_WINDOW = JMLookThroughWindow()

    if restore:
        mixinPtr = omui.MQtUtil.findControl(LOOK_WINDOW.objectName())
        omui.MQtUtil.addWidgetToMayaLayout(long(mixinPtr), long(restored_control))
    else:
        required_control = MAIN_WINDOW.objectName() + 'WorkspaceControl'
        LOOK_WINDOW.show(dockable=True, controls=required_control,
            uiScript='import jmLightToolkit\njmLightToolkit.createLookThroughWindow(restore=True)',
            closeCallback='import jmLightToolkit\njmLightToolkit._lookThroughWindowClosed()')

    LOOK_WINDOW.lookThroughLightSelected()
    return LOOK_WINDOW

def mainWindowClosed():
    """ Close Callback JMLightToolkit UI. """
    global MAIN_WINDOW
    global LOOK_WINDOW
    global FLTR_WINDOW
    if MAIN_WINDOW:
        MAIN_WINDOW = None
        LOOK_WINDOW = None
        FLTR_WINDOW = None

def main(restore=False):
    """ Run JMLightToolkit UI. """
    promptDialogMtoA()
    global MAIN_WINDOW

    if not restore:
        control = __name__ + "WorkspaceControl"
        if pm.workspaceControl(control, q=True, exists=True) and MAIN_WINDOW is None:
            pm.workspaceControl(control, e=True, close=True)
            pm.deleteUI(control)

    if restore:
        restored_control = omui.MQtUtil.getCurrentParent()

    if MAIN_WINDOW is None:
        MAIN_WINDOW = JMLightToolkit()

    if restore:
        mixinPtr = omui.MQtUtil.findControl(MAIN_WINDOW.objectName())
        omui.MQtUtil.addWidgetToMayaLayout(long(mixinPtr), long(restored_control))

    else:
        MAIN_WINDOW.show(dockable=True, minWidth=300, width=400, widthSizingProperty='minimum',
            uiScript='import jmLightToolkit\njmLightToolkit.main(restore=True)',
            closeCallback='import jmLightToolkit\njmLightToolkit.mainWindowClosed()' )

    return MAIN_WINDOW
