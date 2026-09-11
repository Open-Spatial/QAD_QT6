# -*- coding: utf-8 -*-
"""
/***************************************************************************
 QAD Quantum Aided Design plugin ok

 TEXT command to insert a label

                              -------------------
        begin                : 2013-12-31
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
from qgis.core import QgsGeometry, QgsFeature, QgsFields, QgsField, QgsWkbTypes, QgsPointXY, QgsVectorLayerUtils
from qgis.PyQt.QtCore import QVariant
from qgis.PyQt.QtGui import QIcon


from .. import qad_utils
from .qad_generic_cmd import QadCommandClass
from .. import qad_layer
from .. import qad_label
from ..qad_getpoint import QadGetPointDrawModeEnum
from .qad_getdist_cmd import QadGetDistClass
from .qad_getangle_cmd import QadGetAngleClass
from ..qad_dim import QadDimStyles
from ..qad_textwindow import QadInputModeEnum
from ..qad_msg import QadMsg
from ..qad_point import QadPoint


# Class that manages the TEXT command
class QadTEXTCommandClass(QadCommandClass):

   def instantiateNewCmd(self):
      """instantiates a new command of the same type"""
      return QadTEXTCommandClass(self.plugIn)

   def getName(self):
      return QadMsg.translate("Command_list", "TEXT")

   def getEnglishName(self):
      return "TEXT"

   def connectQAction(self, action):
      action.triggered.connect(self.plugIn.runTEXTCommand)

   def getIcon(self):
      return QIcon(":/plugins/qad/icons/text.svg")

   def getNote(self):
      # set the explanatory notes of the command
      return QadMsg.translate("Command_TEXT", "Inserts a text.")

   def __init__(self, plugIn):
      QadCommandClass.__init__(self, plugIn)
      self.insPt = None
      self.hText = self.plugIn.lastHText
      self.rot = self.plugIn.lastRot
      self.GetDistClass = None
      self.GetAngleClass = None
      self.labelFields = None
      self.labelFieldNamesNdx = 0
      self.labelFieldValues = []
      self.scalarTextInputs = False

   def __del__(self):
      QadCommandClass.__del__(self)
      if self.GetDistClass is not None:
         del self.GetDistClass
      if self.GetAngleClass is not None:
         del self.GetAngleClass


   def getPointMapTool(self, drawMode = QadGetPointDrawModeEnum.NONE):
      # when requesting distance (text height)
      if self.step == 2:
         return self.GetDistClass.getPointMapTool()
      # when rotation request is in progress
      elif self.step == 3:
         return self.GetAngleClass.getPointMapTool()
      else:
         return QadCommandClass.getPointMapTool(self, drawMode)


   def getCurrentContextualMenu(self):
      # when requesting distance (text height)
      if self.step == 2:
         return self.GetDistClass.getCurrentContextualMenu()
      # when rotation request is in progress
      elif self.step == 3:
         return self.GetAngleClass.getCurrentContextualMenu()
      else:
         return self.contextualMenu


   def addFeature(self, layer):
      pt = QadPoint(self.insPt)
      g = self.mapToLayerCoordinates(layer, pt.asGeom(layer.wkbType()))
      f = QgsVectorLayerUtils.createFeature(layer, g, {}, layer.createExpressionContext())

      # if the text height depends on only one field
      sizeFldNames = qad_label.get_labelSizeFieldNames(layer)
      if len(sizeFldNames) == 1 and len(sizeFldNames[0]) > 0:
         f.setAttribute(sizeFldNames[0], self.hText)

      # if the rotation depends on only one field
      rotFldNames = qad_label.get_labelRotationFieldNames(layer)
      if len(rotFldNames) == 1 and len(rotFldNames[0]) > 0:
         f.setAttribute(rotFldNames[0], qad_utils.toDegrees(self.rot))

      # set the values of the attributes that make up the label
      i = 0
      tot = len(self.labelFields)
      while i < tot:
         f.setAttribute(self.labelFields[i].name(), self.labelFieldValues[i])
         i = i + 1

      return qad_layer.addFeatureToLayer(self.plugIn, layer, f, None, True, False, False)

   def initLabelFields(self, layer):
      labelFieldNames = qad_label.get_labelFieldNames(layer)
      if len(labelFieldNames) > 0:
         self.labelFields = QgsFields()
         for field in layer.dataProvider().fields():
            if field.name() in labelFieldNames:
               self.labelFields.append(QgsField(field.name(), field.type()))

   # ============================================================================
   # waitForFieldValue
   # ============================================================================
   def waitForFieldValue(self):
      self.step = 4

      if self.labelFields is None:
         return False
      if self.labelFieldNamesNdx >= len(self.labelFields):
         return False
      field = self.labelFields[self.labelFieldNamesNdx]
      if self.scalarTextInputs and field.name().upper() == "TAG_VALUE":
         prompt = QadMsg.translate("Command_TEXT", "Enter text value: ")
      else:
         prompt = QadMsg.translate("Command_TEXT", "Enter the value of attribute \"{0}\": ").format(field.name())
      if field.type() == QVariant.Double: # is preparing to wait for a double or null value
         self.waitForFloat(prompt, None, QadInputModeEnum.NONE)
      elif field.type() == QVariant.LongLong: # prepares to wait for a 64-bit long or null value
         self.waitForLong(prompt, None, QadInputModeEnum.NONE)
      elif field.type() == QVariant.Int: # is preparing to wait for an integer or null value
         self.waitForInt(prompt, None, QadInputModeEnum.NONE)
      elif field.type() == QVariant.Bool: # is preparing to wait for a boolean or null value
         self.waitForBool(prompt, None, QadInputModeEnum.NONE)
      else: # is preparing to wait for a null string or value
         self.waitForString(prompt, None, QadInputModeEnum.NONE)

      return True


   @staticmethod
   def _uses_munsys_text_contract(layer):
      try:
         names = {str(name).upper() for name in layer.fields().names()}
      except Exception:
         return False
      return {
         "NOTE_TYPE",
         "TAG_X",
         "TAG_Y",
         "TAG_VALUE",
         "TAG_SIZE",
         "TAG_ANGLE",
      }.issubset(names)


   def run(self, msgMapTool = False, msg = None):
      if self.plugIn.canvas.mapSettings().destinationCrs().isGeographic():
         self.showMsg(QadMsg.translate("QAD", "\nThe coordinate reference system of the project must be a projected coordinate system.\n"))
         return True # end command

      currLayer, errMsg = qad_layer.getCurrLayerEditable(self.plugIn.canvas, QgsWkbTypes.PointGeometry)
      if currLayer is None:
         self.showErr(errMsg)
         return True # end command

      if qad_layer.isTextLayer(currLayer) == False:
         errMsg = QadMsg.translate("QAD", "\nCurrent layer is not a textual layer.")
         errMsg = errMsg + QadMsg.translate("QAD", "\nA textual layer is a vector punctual layer having a label and the symbol transparency no more than 10%.\n")
         self.showErr(errMsg)
         return True # end command

      # Munsys annotation layers store height and rotation as scalar tag
      # attributes. Keep QAD's point-based TEXT input for ordinary text
      # layers, but do not let map clicks become coordinate-pair values for
      # the Munsys contract.
      self.scalarTextInputs = self._uses_munsys_text_contract(currLayer)

      if  len(QadDimStyles.getDimListByLayer(currLayer)) > 0:
         errMsg = QadMsg.translate("QAD", "\nThe current layer belongs to a dimension style.\n")
         self.showErr(errMsg)
         return True # end command


      # =========================================================================
      # INSERT POINT REQUEST
      if self.step == 0: # start of command
         self.waitForPoint() # is preparing to wait for a point
         self.step = self.step + 1
         return False

      # =========================================================================
      # RESPONSE TO INSERT POINT REQUEST
      elif self.step == 1: # after waiting for a point the command restarts
         if msgMapTool == True: # the point comes from a graphic selection
            # the following condition occurs if while selecting a point
            # another plugin was activated which deactivated Qad
            # so the command that returns here has been reactivated without the map tool
            # has selected a point
            if self.getPointMapTool().point is None: # the map tool was activated without a dot
               if self.getPointMapTool().rightButton == True: # if used with the right mouse button
                  return True # end command
               else:
                  self.setMapTool(self.getPointMapTool()) # I reactivate the map tool
                  return False

            pt = self.getPointMapTool().point
         else: # the dot comes as a parameter of the function
            pt = msg

         self.insPt = QgsPointXY(pt)
         self.plugIn.setLastPoint(self.insPt)

         # if the text height depends on only one field
         sizeFldNames = qad_label.get_labelSizeFieldNames(currLayer)
         if len(sizeFldNames) == 1 and len(sizeFldNames[0]) > 0:
            # prepares to wait for the ladder
            self.GetDistClass = QadGetDistClass(
               self.plugIn,
               allow_points = not self.scalarTextInputs,
            )
            prompt = QadMsg.translate("Command_TEXT", "Specify the text height <{0}>: ")
            self.GetDistClass.msg = prompt.format(str(self.hText))
            self.GetDistClass.dist = self.hText
            self.GetDistClass.inputMode = QadInputModeEnum.NOT_NEGATIVE | QadInputModeEnum.NOT_ZERO
            self.GetDistClass.startPt = self.insPt
            self.step = 2
            self.GetDistClass.run(msgMapTool, msg)
            return False
         else:
            # if the rotation depends on only one field
            rotFldNames = qad_label.get_labelRotationFieldNames(currLayer)
            if len(rotFldNames) == 1 and len(rotFldNames[0]) > 0:
               if self.GetAngleClass is not None:
                  del self.GetAngleClass
               # prepares to wait for the rotation angle
               self.GetAngleClass = QadGetAngleClass(
                  self.plugIn,
                  allow_points = not self.scalarTextInputs,
               )
               prompt = QadMsg.translate("Command_TEXT", "Specify the text rotation <{0}>: ")
               self.GetAngleClass.msg = prompt.format(str(qad_utils.toDegrees(self.rot)))
               self.GetAngleClass.angle = self.rot
               self.GetAngleClass.startPt = self.insPt
               self.step = 3
               self.GetAngleClass.run(msgMapTool, msg)
               return False
            else:
               self.initLabelFields(currLayer)
               if self.waitForFieldValue() == False:
                  self.addFeature(currLayer)
                  return True

         return False

      # =========================================================================
      # RESPONSE TO THE TEXT HEIGHT REQUEST (from step = 1)
      elif self.step == 2:
         if self.GetDistClass.run(msgMapTool, msg) == True:
            if self.GetDistClass.dist is not None:
               self.hText = self.GetDistClass.dist
               self.plugIn.setLastHText(self.hText)
               del self.GetDistClass
               self.GetDistClass = None

               # if the rotation depends on only one field
               rotFldNames = qad_label.get_labelRotationFieldNames(currLayer)
               if len(rotFldNames) == 1 and len(rotFldNames[0]) > 0:
                  if self.GetAngleClass is not None:
                     del self.GetAngleClass
                  # prepares to wait for the rotation angle
                  self.GetAngleClass = QadGetAngleClass(
                     self.plugIn,
                     allow_points = not self.scalarTextInputs,
                  )
                  prompt = QadMsg.translate("Command_TEXT", "Specify the text rotation <{0}>: ")
                  self.GetAngleClass.msg = prompt.format(str(qad_utils.toDegrees(self.rot)))
                  self.GetAngleClass.angle = self.rot
                  self.GetAngleClass.startPt = self.insPt
                  self.step = 3
                  self.GetAngleClass.run(msgMapTool, msg)
                  return False
               else:
                  self.initLabelFields(currLayer)
                  if self.waitForFieldValue() == False:
                     self.addFeature(currLayer)
                     return True
            else:
               return True
         return False

      # =========================================================================
      # RESPONSE TO THE ROTATION REQUEST (from step = 1 or 2)
      elif self.step == 3:
         if self.GetAngleClass.run(msgMapTool, msg) == True:
            if self.GetAngleClass.angle is not None:
               self.rot = self.GetAngleClass.angle
               self.plugIn.setLastRot(self.rot)
               self.initLabelFields(currLayer)
               if self.waitForFieldValue() == False:
                  self.addFeature(currLayer)
                  return True # end command
            else:
               return True
         return False


      # =========================================================================
      # ANSWER TO THE REQUEST FOR THE VALUE OF A FIELD
      elif self.step == 4: # after waiting for a value the command is restarted
         if msgMapTool == True: # the point comes from a graphic selection
            self.waitForFieldValue()
            return False
         # the value comes as a function parameter
         self.labelFieldValues.append(msg)
         self.labelFieldNamesNdx = self.labelFieldNamesNdx + 1
         if self.waitForFieldValue() == False:
            self.addFeature(currLayer)
            return True # end command

         return False

