# -*- coding: utf-8 -*-
"""
/***************************************************************************
 QAD Quantum Aided Design plugin

 base class for a command

                              -------------------
        begin                : 2013-05-22
        copyright            : iiiii
        email                : hhhhh
        developers           : bbbbb aaaaa ggggg
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


# Import the PyQt and QGIS libraries
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtCore import QObject
from qgis.PyQt.QtWidgets import QAction, QMenu
from qgis.core import QgsPointXY, QgsGeometry, QgsCoordinateTransform, QgsProject, QgsWkbTypes


from ..qad_msg import QadMsg
from ..qad_utils import pointToStringFmt
from ..qad_variables import QadVariables
from ..qad_textwindow import QadInputModeEnum, QadInputTypeEnum
from ..qad_getpoint import QadGetPointDrawModeEnum, QadGetPoint, QadGetPointSelectionModeEnum
from ..qad_dynamicinput import QadDynamicInputContextEnum
from ..qad_dsettings_dlg import QadDSETTINGSDialog, QadDSETTINGSTabIndexEnum
from ..qad_snapper import QadSnapTypeEnum, snapTypeEnum2Str


# Class that manages a generic command
class QadCommandClass(QObject): # derived from QObject to handle the sender() method
   def showMsg(self, msg, displayPromptAfterMsg = False):
      if self.plugIn is not None:
         self.plugIn.showMsg(msg, displayPromptAfterMsg)

   def showErr(self, err):
      if self.plugIn is not None:
         self.plugIn.showErr(err)

   def showInputMsg(self, inputMsg, inputType, default = None, keyWords = "", \
                    inputMode = QadInputModeEnum.NONE):
      if self.plugIn is not None:
         self.plugIn.showInputMsg(inputMsg, inputType, default, keyWords, inputMode)

      # I initialize the context menu
      self.initContextualMenu(inputType, keyWords)


   def initContextualMenu(self, inputType, keyWords):
      if self.plugIn is None:
         return

      if self.contextualMenu:
         del self.contextualMenu
         self.contextualMenu = None

#       if keyWords == "":
#          if self.contextualMenu:
#             del self.contextualMenu
#             self.contextualMenu = None
#          return

      self.contextualMenu = QadContextualMenuClass(self.plugIn, inputType, keyWords)


   def enterActionByContextualMenu(self):
      self.plugIn.showEvaluateMsg(None)


   def cancelActionByContextualMenu(self):
      self.plugIn.abortCommand()


   def showEvaluateMsgByContextualMenu(self):
      sender = self.sender()
      self.plugIn.showEvaluateMsg(sender.text())


   def getPointMapTool(self, drawMode = QadGetPointDrawModeEnum.NONE):
      if (self.plugIn is not None):
         if self.PointMapTool is None:
            self.PointMapTool = QadGetPoint(self.plugIn, drawMode) # for selecting a point
         return self.PointMapTool
      else:
         return None


   def getCurrentContextualMenu(self):
      return self.contextualMenu


   def hidePointMapToolMarkers(self):
      if self.PointMapTool is not None:
         self.PointMapTool.hidePointMapToolMarkers()

   def setMapTool(self, mapTool):
      if self.plugIn is not None:
         # set the map tool for input via graphics window
         self.plugIn.canvas.setMapTool(mapTool)
         self.plugIn.mainAction.setChecked(True)


   def waitForPoint(self, msg = None, \
                    default = None, inputMode = QadInputModeEnum.NOT_NULL):
      if msg is None:
          msg = QadMsg.translate("QAD", "Specify point: ")
      self.setMapTool(self.getPointMapTool())
      # set the input via text window
      self.showInputMsg(msg, QadInputTypeEnum.POINT2D, default, "", inputMode)


   def waitForString(self, msg, default = None, inputMode = QadInputModeEnum.NONE):
      self.setMapTool(self.getPointMapTool())
      # set the input via text window
      self.showInputMsg(msg, QadInputTypeEnum.STRING, default, "", inputMode)


   def waitForInt(self, msg, default = None, inputMode = QadInputModeEnum.NOT_NULL):
      self.setMapTool(self.getPointMapTool())
      # set the input via text window
      self.showInputMsg(msg, QadInputTypeEnum.INT, default, "", inputMode)


   def waitForLong(self, msg, default = None, inputMode = QadInputModeEnum.NOT_NULL):
      self.setMapTool(self.getPointMapTool())
      # set the input via text window
      self.showInputMsg(msg, QadInputTypeEnum.LONG, default, "", inputMode)


   def waitForFloat(self, msg, default = None, inputMode = QadInputModeEnum.NOT_NULL):
      self.setMapTool(self.getPointMapTool())
      # set the input via text window
      self.showInputMsg(msg, QadInputTypeEnum.FLOAT, default, "", inputMode)


   def waitForBool(self, msg, default = None, inputMode = QadInputModeEnum.NOT_NULL):
      self.setMapTool(self.getPointMapTool())
      # set the input via text window
      self.showInputMsg(msg, QadInputTypeEnum.BOOL, default, "", inputMode)


   def waitForSelSet(self, msg = QadMsg.translate("QAD", "Select objects: ")):
      self.getPointMapTool().setDrawMode(QadGetPointDrawModeEnum.ELASTIC_RECTANGLE)
      self.setMapTool(self.getPointMapTool())
      self.getPointMapTool().getDynamicInput().context = QadDynamicInputContextEnum.NONE
      # set the input via text window
      self.showInputMsg(msg, QadInputTypeEnum.POINT2D)


   def waitFor(self, msg, inputType, default = None, keyWords = "", \
               inputMode = QadInputModeEnum.NONE):
      self.setMapTool(self.getPointMapTool())
      # set the input via text window
      self.showInputMsg(msg, inputType, default, keyWords, inputMode)

   def setCapturePrompts(self, prompts):
      self.capturePromptOverrides = {}
      self.capturePromptSequenceIndexes = {}
      if type(prompts) != dict:
         return
      for key, value in prompts.items():
         prompt_key = str(key or "").strip().lower()
         if prompt_key == "":
            continue
         if type(value) in (list, tuple):
            prompt_values = [str(item or "") for item in value if str(item or "").strip() != ""]
            if len(prompt_values) > 0:
               self.capturePromptOverrides[prompt_key] = prompt_values
            continue
         prompt_text = str(value or "")
         if prompt_text.strip() != "":
            self.capturePromptOverrides[prompt_key] = prompt_text

   def setCaptureFinishOnPointCount(self, point_count):
      self.captureFinishOnPointCount = None
      try:
         count = int(point_count)
      except Exception:
         return
      if count > 0:
         self.captureFinishOnPointCount = count

   def setCaptureSelectionSteps(self, selection_steps):
      self.captureSelectionSteps = []
      self.captureSelectionIndex = 0
      self.captureSelections = []
      if type(selection_steps) not in (list, tuple):
         return
      for step in selection_steps:
         if type(step) != dict:
            continue
         prompt = str(step.get("prompt") or "").strip()
         key = str(step.get("key") or "").strip()
         if prompt == "":
            continue
         clean_step = {
            "key": key,
            "prompt": prompt,
            "error_prompt": str(step.get("error_prompt") or step.get("error") or "").strip(),
         }
         layer_ids = []
         for layer_id in step.get("layer_ids") or step.get("allowed_layer_ids") or []:
            value = str(layer_id or "").strip()
            if value != "":
               layer_ids.append(value)
         if len(layer_ids) > 0:
            clean_step["layer_ids"] = layer_ids

         geometry_types = []
         for geom_type in step.get("geometry_types") or []:
            value = str(geom_type or "").strip().lower()
            if value in ("point", "line", "polygon"):
               geometry_types.append(value)
         if len(geometry_types) > 0:
            clean_step["geometry_types"] = geometry_types
         self.captureSelectionSteps.append(clean_step)

   def hasPendingCaptureSelectionStep(self):
      if getattr(self, "virtualCmd", False) == False:
         return False
      return self.captureSelectionIndex < len(self.captureSelectionSteps)

   def waitForCaptureSelectionStep(self):
      step = self.captureSelectionSteps[self.captureSelectionIndex]
      map_tool = self.getPointMapTool()
      map_tool.setSelectionMode(QadGetPointSelectionModeEnum.ENTITY_SELECTION)
      map_tool.layersToCheck = self.captureSelectionLayers(step)

      geometry_types = step.get("geometry_types")
      if type(geometry_types) in (list, tuple) and len(geometry_types) > 0:
         map_tool.checkPointLayer = "point" in geometry_types
         map_tool.checkLineLayer = "line" in geometry_types
         map_tool.checkPolygonLayer = "polygon" in geometry_types
      else:
         map_tool.checkPointLayer = True
         map_tool.checkLineLayer = True
         map_tool.checkPolygonLayer = True

      self.waitFor(step.get("prompt"), QadInputTypeEnum.POINT2D, None, "", QadInputModeEnum.NONE)

   def captureSelectionLayers(self, step):
      layer_ids = step.get("layer_ids")
      if type(layer_ids) not in (list, tuple) or len(layer_ids) == 0:
         return None
      try:
         layers_by_id = QgsProject.instance().mapLayers()
      except Exception:
         layers_by_id = {}
      layers = []
      for layer_id in layer_ids:
         layer = layers_by_id.get(str(layer_id))
         if layer is not None:
            layers.append(layer)
      return layers

   def consumeCaptureSelectionStep(self, msgMapTool = False, msg = None):
      if not self.hasPendingCaptureSelectionStep():
         return None

      step = self.captureSelectionSteps[self.captureSelectionIndex]
      if msgMapTool == True:
         if self.getPointMapTool().point is None:
            if self.getPointMapTool().rightButton == True:
               return None
            self.setMapTool(self.getPointMapTool())
            return False
         point = self.getPointMapTool().point
         entity = self.getPointMapTool().entity
      else:
         point = msg
         entity = self.getPointMapTool().entity

      if point is None or entity is None or entity.isInitialized() == False:
         error_prompt = step.get("error_prompt") or QadMsg.translate("QAD", "\nNo object selected.")
         self.showMsg(error_prompt)
         self.waitForCaptureSelectionStep()
         return False

      layer = entity.layer
      feature_id = entity.featureId
      if self.isCaptureSelectionValid(step, layer) == False:
         error_prompt = step.get("error_prompt") or QadMsg.translate("QAD", "\nIncorrect object selected.")
         self.showMsg(error_prompt)
         self.waitForCaptureSelectionStep()
         return False

      self.captureSelections.append({
         "key": step.get("key") or "",
         "layer_id": layer.id() if layer is not None else "",
         "layer_name": layer.name() if layer is not None else "",
         "feature_id": feature_id,
         "point": QgsPointXY(point),
      })
      self.captureSelectionIndex = self.captureSelectionIndex + 1
      return QgsPointXY(point)

   def isCaptureSelectionValid(self, step, layer):
      if layer is None:
         return False
      layer_ids = step.get("layer_ids")
      if type(layer_ids) in (list, tuple) and len(layer_ids) > 0:
         try:
            if str(layer.id()) not in layer_ids:
               return False
         except Exception:
            return False
      geometry_types = step.get("geometry_types")
      if type(geometry_types) in (list, tuple) and len(geometry_types) > 0:
         try:
            geom_type = layer.geometryType()
         except Exception:
            geom_type = None
         if geom_type == QgsWkbTypes.PointGeometry and "point" not in geometry_types:
            return False
         if geom_type == QgsWkbTypes.LineGeometry and "line" not in geometry_types:
            return False
         if geom_type == QgsWkbTypes.PolygonGeometry and "polygon" not in geometry_types:
            return False
      return True

   def capturedSelections(self):
      return list(self.captureSelections)

   def shouldFinishVirtualCapture(self, point_count):
      if getattr(self, "virtualCmd", False) == False:
         return False
      finish_count = getattr(self, "captureFinishOnPointCount", None)
      if finish_count is None:
         return False
      try:
         return int(point_count) >= int(finish_count)
      except Exception:
         return False

   def capturePrompt(self, key, default):
      prompt_key = str(key or "").strip().lower()
      prompts = getattr(self, "capturePromptOverrides", {})
      if type(prompts) == dict:
         prompt = prompts.get(prompt_key)
         if prompt is not None and str(prompt).strip() != "":
            return str(prompt)
      return default

   def capturePointPrompt(self, menuKey, nextPointKey, default):
      prompt = self.capturePromptSequence(nextPointKey + "_sequence")
      if prompt is not None:
         return prompt

      prompt = self.capturePrompt(menuKey, None)
      if prompt is not None:
         return prompt

      prompt = self.capturePrompt(nextPointKey, None)
      if prompt is not None:
         return prompt

      return default

   def capturePromptSequence(self, key):
      prompt_key = str(key or "").strip().lower()
      prompts = getattr(self, "capturePromptOverrides", {})
      if type(prompts) != dict:
         return None
      prompt_values = prompts.get(prompt_key)
      if type(prompt_values) not in (list, tuple) or len(prompt_values) == 0:
         return None

      indexes = getattr(self, "capturePromptSequenceIndexes", {})
      if type(indexes) != dict:
         indexes = {}
         self.capturePromptSequenceIndexes = indexes
      idx = indexes.get(prompt_key, 0)
      try:
         idx = int(idx)
      except Exception:
         idx = 0
      if idx < 0:
         idx = 0
      if idx >= len(prompt_values):
         return None

      indexes[prompt_key] = idx + 1
      prompt = str(prompt_values[idx] or "")
      return prompt if prompt.strip() != "" else None


   def getCurrMsgFromTxtWindow(self):
      if self.plugIn is not None:
         return self.plugIn.getCurrMsgFromTxtWindow()
      else:
         return None

   def showEvaluateMsg(self, msg = None):
      if self.plugIn is not None:
         self.plugIn.showEvaluateMsg(msg)

   def runCommandAbortingTheCurrent(self):
      self.plugIn.runCommandAbortingTheCurrent(self.getName())

   def getToolTipText(self):
      text = self.getName()
      if len(self.getNote()) > 0:
         text = text + "\n\n" + self.getNote()
      return text

   # ============================================================================
   # functions to be overridden with the classes inherited from this one
   # ============================================================================
   def getName(self):
      """set the command name in uppercase"""
      return ""

   def getEnglishName(self):
      """set the command name to uppercase English"""
      return ""

   def connectQAction(self, action):
      pass
      #action.triggered.connect(self.plugIn.runPLINECommand) ad esempio

   def getIcon(self):
      # set the command icon (e.g. QIcon(":/plugins/qad/icons/pline.svg"))
      # remember to insert the icon into resources.qrc and recompile the resources
      return None

   def getNote(self):
      """set the explanatory notes of the command"""
      return ""

   def __init__(self, plugIn):
      QObject.__init__(self)
      self.plugIn       = plugIn
      self.PointMapTool = None
      self.step         = 0
      self.isValidPreviousInput = True # to manage the command also in macros
      self.contextualMenu = None
      self.capturePromptOverrides = {}
      self.capturePromptSequenceIndexes = {}
      self.captureFinishOnPointCount = None
      self.captureSelectionSteps = []
      self.captureSelectionIndex = 0
      self.captureSelections = []

      # initialize all the map tools necessary for the command
      # example of the structure of a command that requires
      # 1) one point
      # self.mapTool = QadGetPoint(self.plugIn) # for selecting a point


   def __del__(self):
      """ distruttore """
      self.hidePointMapToolMarkers()

      if self.PointMapTool:
         self.PointMapTool.removeItems()
         del self.PointMapTool
         self.PointMapTool = None

      if self.contextualMenu:
         #QObject.disconnect(enterAction, SIGNAL("triggered()"), self.enterActionByContextualMenu)

         del self.contextualMenu
         self.contextualMenu = None


   def instantiateNewCmd(self):
      """instantiates a new command of the same type"""
      return None

   def run(self, msgMapTool = False, msg = None):
      """Execute the command.
            - msgMapTool; if True it means that a value arrives from the command's MapTool
                          if false it means that the value is in the msg parameter
            - msg;        input value to the command (used when msgMapTool = False)

            returns True if the command is completed otherwise False
      """
      # example of the structure of a command that requires
      # 1) one point
      if self.step == 0: # start of command
         self.waitForPoint() # is preparing to wait for a point
         self.step = self.step + 1
         return False
      elif self.step == 1: # after waiting for a point the command restarts
         if msgMapTool == True: # the point comes from a graphic selection
            # the following condition occurs if while selecting a point
            # Another plugin was activated which deactivated Qad
            # so the command that returns here has been reactivated without the map tool
            # has selected a point
            if self.getPointMapTool().point is None: # the map tool was activated without a dot
               self.setMapTool(self.getPointMapTool()) # I reactivate the map tool
               return False

            pt = self.getPointMapTool().point
         else: # the dot comes as a parameter of the function
            pt = msg

         return True

   def mapToLayerCoordinates(self, layer, point_geom):
      # transform point or geometry coordinates from output CRS to layer's CRS
      if self.plugIn is None:
         return None
      if type(point_geom) == QgsPointXY:
         return self.plugIn.canvas.mapSettings().mapToLayerCoordinates(layer, point_geom)

      fromCrs = self.plugIn.canvas.mapSettings().destinationCrs()
      toCrs = layer.crs()

      if type(point_geom) == QgsGeometry:
         if fromCrs == toCrs:
            return QgsGeometry(point_geom)

         # I transform the geometry in the canvas crs to work with xy plane coordinates
         coordTransform = QgsCoordinateTransform(self.plugIn.canvas.mapSettings().destinationCrs(), \
                                                 layer.crs(), \
                                                 QgsProject.instance())
         g = QgsGeometry(point_geom)
         g.transform(coordTransform)
         return g
      elif (type(point_geom) == list or type(point_geom) == tuple): # list of points or geometries
         res = []
         if fromCrs == toCrs:
            for pt in point_geom:
               if type(pt) == QgsPointXY:
                  res.append(QgsPointXY(pt))
               elif type(pt) == QgsGeometry:
                  res.append(QgsGeometry(pt))
            return res

         coordTransform = QgsCoordinateTransform(self.plugIn.canvas.mapSettings().destinationCrs(), \
                                                 layer.crs(), \
                                                 QgsProject.instance())
         for pt in point_geom:
            if type(pt) == QgsPointXY:
               res.append(coordTransform.transform(pt))
            elif type(pt) == QgsGeometry:
               g = QgsGeometry(pt)
               g.transform(coordTransform)
               res.append(g)
         return res
      else:
         return None

   def layerToMapCoordinates(self, layer, point_geom):
      # transform point or geometry coordinates from layer's CRS to output CRS
      if self.plugIn is None:
         return None
      if type(point_geom) == QgsPointXY:
         return self.plugIn.canvas.mapSettings().layerToMapCoordinates(layer, point_geom)
      elif type(point_geom) == QgsGeometry:
         # I transform the geometry in the canvas crs to work with xy plane coordinates
         coordTransform = QgsCoordinateTransform(layer.crs(), \
                                                 self.plugIn.canvas.mapSettings().destinationCrs(), \
                                                 QgsProject.instance())
         g = QgsGeometry(point_geom)
         g.transform(coordTransform)
         return g
      elif (type(point_geom) == list or type(point_geom) == tuple): # list of points or geometries
         coordTransform = QgsCoordinateTransform(self.plugIn.canvas.mapSettings().destinationCrs(), \
                                                 layer.crs(), \
                                                 QgsProject.instance())
         res = []
         for pt in point_geom:
            if type(pt) == QgsPointXY:
               res.append(coordTransform.transform(pt))
            elif type(point_geom) == QgsGeometry:
               g = QgsGeometry(point_geom)
               g.transform(coordTransform)
               res.append(g)
         return res
      else:
         return None


# Class that manages the context menu of Qad commands
class QadContextualMenuClass(QMenu):

   def __init__(self, plugIn, inputType, keyWords):
      self.plugIn = plugIn
      QMenu.__init__(self, self.plugIn.canvas)
      self.connections = []
      self.localEnglishKeyWords = []
      self.localKeyWords = []
      self.initActions(inputType, keyWords)

   def __del__(self):
      """ distruttore """
      self.delActions()


   def delActions(self):
      # delete and disconnect all actions for events
      for connection in self.connections:
         action = connection[0]
         slot = connection[1]
         action.triggered.disconnect(slot)
      del self.connections[:]


   def initActions(self, inputType, keyWords):
      self.delActions()

      msg = QadMsg.translate("ContextualCmdMenu", "Enter")
      action = QAction(msg, self)
      self.addAction(action)
      self.connections.append([action, self.enterActionByContextualMenu])

      msg = QadMsg.translate("ContextualCmdMenu", "Cancel")
      action = QAction(msg, self)
      self.addAction(action)
      self.connections.append([action, self.cancelActionByContextualMenu])

      if inputType & QadInputTypeEnum.POINT2D or inputType & QadInputTypeEnum.POINT3D:
         msg = QadMsg.translate("ContextualCmdMenu", "Recent Input")
         recentPtsMenu = self.addMenu(msg)

         ptsHistory = self.plugIn.ptsHistory
         ptsHistoryLen = len(ptsHistory)
         i = ptsHistoryLen - 1
         cmdInputHistoryMax = QadVariables.get(QadMsg.translate("Environment variables", "CMDINPUTHISTORYMAX"))
         # cycle on the history of the last points used
         while i >= 0 and (ptsHistoryLen - i) <= cmdInputHistoryMax:
            strPt = pointToStringFmt(ptsHistory[i])
            i = i - 1
            action = QAction(strPt, recentPtsMenu)
            recentPtsMenu.addAction(action)
            self.connections.append([action, self.showEvaluateMsgByContextualMenu])

      # loop over the current options of the command in use
      if len(keyWords) > 0:
         # initialize the list of keywords contextual to the current command (local language)
         # separator character between local language and English keywords
         self.localEnglishKeyWords = keyWords.split("_")
         self.localKeyWords = self.localEnglishKeyWords[0].split("/") # carattere separatore delle parole chiave

         self.addSeparator()
         for keyWord in self.localKeyWords:
            action = QAction(keyWord, self)
            self.addAction(action)
            self.connections.append([action, self.showEvaluateMsgByContextualMenu])
      else: # there are no options
         del self.localEnglishKeyWords[:] # I empty the list
         del self.localKeyWords[:] # I empty the list

      if inputType & QadInputTypeEnum.POINT2D or inputType & QadInputTypeEnum.POINT3D:
         self.addSeparator()
         osnapMenu = QadOsnapContextualMenuClass(self.plugIn)
         self.addMenu(osnapMenu)

      # create all the connections for the events
      for connection in self.connections:
         action = connection[0]
         slot = connection[1]
         action.triggered.connect(slot)


   def enterActionByContextualMenu(self):
      actualCmd = self.plugIn.QadCommands.actualCommand
      if actualCmd is not None:
         pointMapTool = actualCmd.getPointMapTool()
         if pointMapTool is not None:
            dynInput = pointMapTool.getDynamicInput()
            if dynInput is not None:
               if dynInput.anyLockedValueEdit() == True:
                  submitCurrentInput = getattr(dynInput, "submitCurrentInput", None)
                  if callable(submitCurrentInput):
                     # Keep context-menu Enter consistent with keyboard Enter.
                     # In particular, refreshResult() treats an edited point
                     # coordinate as a point and therefore bypasses keywords
                     # such as Justify and text values entered in that widget.
                     submitCurrentInput()
                     return
                  if dynInput.refreshResult() == True:
                     dynInput.showEvaluateMsg(dynInput.resStr)
                     return

      self.plugIn.showEvaluateMsg(None)


   def cancelActionByContextualMenu(self):
      self.plugIn.abortCommand()


   def showEvaluateMsgByContextualMenu(self):
      sender = self.sender()
      self.plugIn.showEvaluateMsg(sender.text())


# Class that manages the osnap context menu of Qad commands
class QadOsnapContextualMenuClass(QMenu):

   def __init__(self, plugIn):
      self.plugIn = plugIn
      title = QadMsg.translate("ContextualCmdMenu", "Snap Overrides")
      QMenu.__init__(self, title, self.plugIn.canvas)
      self.connections = []
      self.initActions()

   def __del__(self):
      """ distruttore """
      self.delActions()


   def delActions(self):
      # delete and disconnect all actions for events
      for connection in self.connections:
         action = connection[0]
         slot = connection[1]
         action.triggered.disconnect(slot)
      del self.connections[:]


   def initActions(self):
      self.delActions()

      msg = QadMsg.translate("Snap", "Midpoint between 2 points")
      icon = QIcon(":/plugins/qad/icons/osnap_mid2p.svg")
      if icon is None:
         M2PAction = QAction(msg, self)
      else:
         M2PAction = QAction(icon, msg, self)
      self.addAction(M2PAction)
      self.connections.append([M2PAction, self.addM2PActionByPopupMenu])

      self.addSeparator()

      msg = QadMsg.translate("DSettings_Dialog", "Start / End")
      icon = QIcon(":/plugins/qad/icons/osnap_endLine.svg")
      if icon is None:
         addEndLineSnapTypeAction = QAction(msg, self)
      else:
         addEndLineSnapTypeAction = QAction(icon, msg, self)
      self.addAction(addEndLineSnapTypeAction)
      self.connections.append([addEndLineSnapTypeAction, self.addEndLineSnapTypeByPopupMenu])

      msg = QadMsg.translate("DSettings_Dialog", "Segment Start / End")
      icon = QIcon(":/plugins/qad/icons/osnap_end.svg")
      if icon is None:
         addEndSnapTypeAction = QAction(msg, self)
      else:
         addEndSnapTypeAction = QAction(icon, msg, self)
      self.addAction(addEndSnapTypeAction)
      self.connections.append([addEndSnapTypeAction, self.addEndSnapTypeByPopupMenu])

      msg = QadMsg.translate("DSettings_Dialog", "Middle point")
      icon = QIcon(":/plugins/qad/icons/osnap_mid.svg")
      if icon is None:
         addMidSnapTypeAction = QAction(msg, self)
      else:
         addMidSnapTypeAction = QAction(icon, msg, self)
      self.addAction(addMidSnapTypeAction)
      self.connections.append([addMidSnapTypeAction, self.addMidSnapTypeByPopupMenu])

      msg = QadMsg.translate("DSettings_Dialog", "Intersection")
      icon = QIcon(":/plugins/qad/icons/osnap_int.svg")
      if icon is None:
         addIntSnapTypeAction = QAction(msg, self)
      else:
         addIntSnapTypeAction = QAction(icon, msg, self)
      self.addAction(addIntSnapTypeAction)
      self.connections.append([addIntSnapTypeAction, self.addIntSnapTypeByPopupMenu])

      msg = QadMsg.translate("DSettings_Dialog", "Intersection on extension")
      icon = QIcon(":/plugins/qad/icons/osnap_extInt.svg")
      if icon is None:
         addExtIntSnapTypeAction = QAction(msg, self)
      else:
         addExtIntSnapTypeAction = QAction(icon, msg, self)
      self.addAction(addExtIntSnapTypeAction)
      self.connections.append([addExtIntSnapTypeAction, self.addExtIntSnapTypeByPopupMenu])

      msg = QadMsg.translate("DSettings_Dialog", "Extend")
      icon = QIcon(":/plugins/qad/icons/osnap_ext.svg")
      if icon is None:
         addExtSnapTypeAction = QAction(msg, self)
      else:
         addExtSnapTypeAction = QAction(icon, msg, self)
      self.addAction(addExtSnapTypeAction)
      self.connections.append([addExtSnapTypeAction, self.addExtSnapTypeByPopupMenu])

      self.addSeparator()

      msg = QadMsg.translate("DSettings_Dialog", "Center")
      icon = QIcon(":/plugins/qad/icons/osnap_cen.svg")
      if icon is None:
         addCenSnapTypeAction = QAction(msg, self)
      else:
         addCenSnapTypeAction = QAction(icon, msg, self)
      self.addAction(addCenSnapTypeAction)
      self.connections.append([addCenSnapTypeAction, self.addCenSnapTypeByPopupMenu])

      msg = QadMsg.translate("DSettings_Dialog", "Quadrant")
      icon = QIcon(":/plugins/qad/icons/osnap_qua.svg")
      if icon is None:
         addQuaSnapTypeAction = QAction(msg, self)
      else:
         addQuaSnapTypeAction = QAction(icon, msg, self)
      self.addAction(addQuaSnapTypeAction)
      self.connections.append([addQuaSnapTypeAction, self.addQuaSnapTypeByPopupMenu])

      msg = QadMsg.translate("DSettings_Dialog", "Tangent")
      icon = QIcon(":/plugins/qad/icons/osnap_tan.svg")
      if icon is None:
         addTanSnapTypeAction = QAction(msg, self)
      else:
         addTanSnapTypeAction = QAction(icon, msg, self)
      self.addAction(addTanSnapTypeAction)
      self.connections.append([addTanSnapTypeAction, self.addTanSnapTypeByPopupMenu])

      self.addSeparator()

      msg = QadMsg.translate("DSettings_Dialog", "Perpendicular")
      icon = QIcon(":/plugins/qad/icons/osnap_per.svg")
      if icon is None:
         addPerSnapTypeAction = QAction(msg, self)
      else:
         addPerSnapTypeAction = QAction(icon, msg, self)
      self.addAction(addPerSnapTypeAction)
      self.connections.append([addPerSnapTypeAction, self.addPerSnapTypeByPopupMenu])

      msg = QadMsg.translate("DSettings_Dialog", "Parallel")
      icon = QIcon(":/plugins/qad/icons/osnap_par.svg")
      if icon is None:
         addParSnapTypeAction = QAction(msg, self)
      else:
         addParSnapTypeAction = QAction(icon, msg, self)
      self.addAction(addParSnapTypeAction)
      self.connections.append([addParSnapTypeAction, self.addParSnapTypeByPopupMenu])

      msg = QadMsg.translate("DSettings_Dialog", "Node")
      icon = QIcon(":/plugins/qad/icons/osnap_nod.svg")
      if icon is None:
         addNodSnapTypeAction = QAction(msg, self)
      else:
         addNodSnapTypeAction = QAction(icon, msg, self)
      self.addAction(addNodSnapTypeAction)
      self.connections.append([addNodSnapTypeAction, self.addNodSnapTypeByPopupMenu])

      msg = QadMsg.translate("DSettings_Dialog", "Near")
      icon = QIcon(":/plugins/qad/icons/osnap_nea.svg")
      if icon is None:
         addNeaSnapTypeAction = QAction(msg, self)
      else:
         addNeaSnapTypeAction = QAction(icon, msg, self)
      self.addAction(addNeaSnapTypeAction)
      self.connections.append([addNeaSnapTypeAction, self.addNeaSnapTypeByPopupMenu])

      msg = QadMsg.translate("DSettings_Dialog", "Progressive")
      icon = QIcon(":/plugins/qad/icons/osnap_pr.svg")
      if icon is None:
         addPrSnapTypeAction = QAction(msg, self)
      else:
         addPrSnapTypeAction = QAction(icon, msg, self)
      self.addAction(addPrSnapTypeAction)
      self.connections.append([addPrSnapTypeAction, self.addPrSnapTypeByPopupMenu])

      msg = QadMsg.translate("DSettings_Dialog", "None")
      icon = QIcon(":/plugins/qad/icons/osnap_disable.svg")
      if icon is None:
         setSnapTypeToDisableAction = QAction(msg, self)
      else:
         setSnapTypeToDisableAction = QAction(icon, msg, self)
      self.addAction(setSnapTypeToDisableAction)
      self.connections.append([setSnapTypeToDisableAction, self.setSnapTypeToDisableByPopupMenu])

      self.addSeparator()

      msg = QadMsg.translate("DSettings_Dialog", "Object snap settings...")
      icon = QIcon(":/plugins/qad/icons/dsettings.svg")
      if icon is None:
         DSettingsAction = QAction(msg, self)
      else:
         DSettingsAction = QAction(icon, msg, self)
      self.addAction(DSettingsAction)
      self.connections.append([DSettingsAction, self.showDSettingsByPopUpMenu])

      # create all the connections for the events
      for connection in self.connections:
         action = connection[0]
         slot = connection[1]
         action.triggered.connect(slot)


   # ============================================================================
   # addSnapTypeByPopupMenu
   # ============================================================================
   def addSnapTypeByPopupMenu(self, _snapType):
      # the function should only set object snap temporarily
      str = snapTypeEnum2Str(_snapType)
      self.plugIn.showEvaluateMsg(str)
      return
#       value = QadVariables.get(QadMsg.translate("Environment variables", "OSMODE"))
#       if value & QadSnapTypeEnum.DISABLE:
#          value =  value - QadSnapTypeEnum.DISABLE
#       QadVariables.set(QadMsg.translate("Environment variables", "OSMODE"), value | _snapType)
#       QadVariables.save()
#       self.plugIn.refreshCommandMapToolSnapType()

   def addM2PActionByPopupMenu(self):
      self.plugIn.showEvaluateMsg("_M2P")
   def addEndLineSnapTypeByPopupMenu(self):
      self.addSnapTypeByPopupMenu(QadSnapTypeEnum.END_PLINE)
   def addEndSnapTypeByPopupMenu(self):
      self.addSnapTypeByPopupMenu(QadSnapTypeEnum.END)
   def addMidSnapTypeByPopupMenu(self):
      self.addSnapTypeByPopupMenu(QadSnapTypeEnum.MID)
   def addIntSnapTypeByPopupMenu(self):
      self.addSnapTypeByPopupMenu(QadSnapTypeEnum.INT)
   def addExtIntSnapTypeByPopupMenu(self):
      self.addSnapTypeByPopupMenu(QadSnapTypeEnum.EXT_INT)
   def addExtSnapTypeByPopupMenu(self):
      self.addSnapTypeByPopupMenu(QadSnapTypeEnum.EXT)
   def addCenSnapTypeByPopupMenu(self):
      self.addSnapTypeByPopupMenu(QadSnapTypeEnum.CEN)
   def addQuaSnapTypeByPopupMenu(self):
      self.addSnapTypeByPopupMenu(QadSnapTypeEnum.QUA)
   def addTanSnapTypeByPopupMenu(self):
      self.addSnapTypeByPopupMenu(QadSnapTypeEnum.TAN)
   def addPerSnapTypeByPopupMenu(self):
      self.addSnapTypeByPopupMenu(QadSnapTypeEnum.PER)
   def addParSnapTypeByPopupMenu(self):
      self.addSnapTypeByPopupMenu(QadSnapTypeEnum.PAR)
   def addNodSnapTypeByPopupMenu(self):
      self.addSnapTypeByPopupMenu(QadSnapTypeEnum.NOD)
   def addNeaSnapTypeByPopupMenu(self):
      self.addSnapTypeByPopupMenu(QadSnapTypeEnum.NEA)
   def addPrSnapTypeByPopupMenu(self):
      self.addSnapTypeByPopupMenu(QadSnapTypeEnum.PR)

   def setSnapTypeToDisableByPopupMenu(self):
      value = QadVariables.get(QadMsg.translate("Environment variables", "OSMODE"))
      QadVariables.set(QadMsg.translate("Environment variables", "OSMODE"), value | QadSnapTypeEnum.DISABLE)
      QadVariables.save()
      self.plugIn.refreshCommandMapToolSnapType()

   def showDSettingsByPopUpMenu(self):
      d = QadDSETTINGSDialog(self.plugIn)
      d.exec()
      self.plugIn.refreshCommandMapToolSnapType()
      self.plugIn.refreshCommandMapToolAutoSnap()
      self.plugIn.refreshCommandMapToolDynamicInput()
