# -*- coding: utf-8 -*-
"""
/***************************************************************************
 QAD Quantum Aided Design plugin

 command to insert into other commands to request a distance

                              -------------------
        begin                : 2013-12-03
        copyright            : iiiii
        email                : hhhhh
        developers           : bbbbb aaaaa gggg
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
from qgis.core import QgsPointXY


from .qad_generic_cmd import QadCommandClass
from ..qad_msg import QadMsg
from ..qad_textwindow import QadInputModeEnum, QadInputTypeEnum
from ..qad_getpoint import QadGetPointDrawModeEnum
from .. import qad_utils
from ..qad_entity import QadEntity


# ===============================================================================
# QadGetDistClass
# ===============================================================================
class QadGetDistClass(QadCommandClass):

   def instantiateNewCmd(self):
      """instantiates a new command of the same type"""
      return QadGetDistClass(self.plugIn)

   def __init__(self, plugIn, *, allow_points = True):
      QadCommandClass.__init__(self, plugIn)
      self.entity = QadEntity()
      self.startPt = None
      self.msg = QadMsg.translate("QAD", "Specify the distance: ")
      self.dist = None
      self.allowPoints = bool(allow_points)
      self.inputMode = QadInputModeEnum.NOT_ZERO | QadInputModeEnum.NOT_NEGATIVE
      self.ctrlKey = False

      # I store last point because the point(s) indicated by this function must not
      # alterare lastpoint
      self.__prevLastPoint = self.plugIn.lastPoint

   def run(self, msgMapTool = False, msg = None):
      if self.plugIn.canvas.mapSettings().destinationCrs().isGeographic():
         self.showMsg(QadMsg.translate("QAD", "\nThe coordinate reference system of the project must be a projected coordinate system.\n"))
         return True # end command

      # =========================================================================
      # POINT or ENTITY REQUEST
      if self.step == 0: # start of command
         # is preparing to wait for a point or a real number
         # msg, inputType, default, keyWords, positive values
         inputType = QadInputTypeEnum.POINT2D | QadInputTypeEnum.FLOAT \
            if self.allowPoints else QadInputTypeEnum.FLOAT
         if self.allowPoints:
            self.waitFor(self.msg, \
                         inputType, \
                         self.dist, "", \
                         QadInputModeEnum.NOT_NULL | self.inputMode)
         else:
            self.plugIn.setStandardMapTool()
            self.showInputMsg(self.msg, \
                              inputType, \
                              self.dist, "", \
                              QadInputModeEnum.NOT_NULL | self.inputMode)

         if self.allowPoints and self.startPt is not None:
            # set the map tool
            self.getPointMapTool().setDrawMode(QadGetPointDrawModeEnum.ELASTIC_LINE)
            self.getPointMapTool().setStartPoint(self.startPt)

         self.step = 1
         return False

      # =========================================================================
      # RESPONSE TO THE REQUEST POINT or real number
      elif self.step == 1: # after waiting for a point the command restarts
         if msgMapTool == True: # the point comes from a graphic selection
            # the following condition occurs if while selecting a point
            # Another plugin was activated which deactivated Qad
            # so the command that returns here has been reactivated without the map tool
            # has selected a point
            if self.getPointMapTool().point is None: # the map tool was activated without a dot
               if self.getPointMapTool().rightButton == True: # if used with the right mouse button
                  return True # end command
               else:
                  self.setMapTool(self.getPointMapTool()) # I reactivate the map tool
                  return False

            value = self.getPointMapTool().point
            self.ctrlKey = self.getPointMapTool().ctrlKey
         else: # the point or real number comes as a function parameter
            value = msg

         if value is None:
            return True # end command

         if type(value) == float:
            self.dist = value
            return True # end command
         elif type(value) == QgsPointXY:
            if not self.allowPoints:
               return True
            # the point(s) indicated by this function must not alter lastpoint
            self.plugIn.setLastPoint(self.__prevLastPoint)

            if self.startPt is not None:
               self.dist = qad_utils.getDistance(self.startPt, value)
               return True # end command
            else:
               self.startPt = value
               # set the map tool
               self.getPointMapTool().setDrawMode(QadGetPointDrawModeEnum.ELASTIC_LINE)
               self.getPointMapTool().setStartPoint(self.startPt)

               # is preparing to wait for a point
               self.waitForPoint(QadMsg.translate("QAD", "Specify second point: "))

               self.step = 2

         return False

      # =========================================================================
      # RESPONSE TO THE REQUEST SECOND POINT OF THE DISTANCE (from step = 1)
      elif self.step == 2: # after waiting for a point the command restarts
         if msgMapTool == True: # the point comes from a graphic selection
            # the following condition occurs if while selecting a point
            # Another plugin was activated which deactivated Qad
            # so the command that returns here has been reactivated without the map tool
            # has selected a point
            if self.getPointMapTool().point is None: # the map tool was activated without a dot
               if self.getPointMapTool().rightButton == True: # if used with the right mouse button
                  return True # end command
               else:
                  self.setMapTool(self.getPointMapTool()) # I reactivate the map tool
                  return False

            value = self.getPointMapTool().point
         else: # the dot comes as a parameter of the function
            value = msg

         # the point(s) indicated by this function must not alter lastpoint
         self.plugIn.setLastPoint(self.__prevLastPoint)

         self.dist = qad_utils.getDistance(self.startPt, value)
         return True # end command
