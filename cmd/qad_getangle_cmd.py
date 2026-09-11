# -*- coding: utf-8 -*-
"""
/***************************************************************************
 QAD Quantum Aided Design plugin

 command to insert into other commands to request an angle

                              -------------------
        begin                : 2013-12-04
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
from qgis.core import QgsPointXY


from .qad_generic_cmd import QadCommandClass
from ..qad_msg import QadMsg
from ..qad_textwindow import QadInputTypeEnum, QadInputModeEnum
from ..qad_entity import QadEntity
from ..qad_getpoint import QadGetPointDrawModeEnum
from .. import qad_utils


# ===============================================================================
# QadGetAngleClass
# ===============================================================================
class QadGetAngleClass(QadCommandClass):

   def instantiateNewCmd(self):
      """instantiates a new command of the same type"""
      return QadGetAngleClass(self.plugIn)

   def __init__(self, plugIn, *, allow_points = True):
      QadCommandClass.__init__(self, plugIn)
      self.entity = QadEntity()
      self.startPt = None
      self.msg = QadMsg.translate("QAD", "Specify angle: ")
      self.angle = None # in radianti
      self.allowPoints = bool(allow_points)
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
         if self.allowPoints and self.startPt is not None:
            # set the map tool
            self.getPointMapTool().setDrawMode(QadGetPointDrawModeEnum.ELASTIC_LINE)
            self.getPointMapTool().setStartPoint(self.startPt)

         # is preparing to wait for a point or a real number
         # msg, inputType, default, keyWords, non-null values
         inputType = QadInputTypeEnum.POINT2D | QadInputTypeEnum.ANGLE \
            if self.allowPoints else QadInputTypeEnum.ANGLE
         if self.allowPoints:
            self.waitFor(self.msg, \
                         inputType, \
                         self.angle, "", \
                         QadInputModeEnum.NOT_NULL)
         else:
            self.plugIn.setStandardMapTool()
            self.showInputMsg(self.msg, \
                              inputType, \
                              self.angle, "", \
                              QadInputModeEnum.NOT_NULL)

         self.step = 1
         return False

      # =========================================================================
      # RESPONSE TO THE POINT OR REAL NUMBER REQUEST
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
         else: # the point or real number comes as a function parameter
            value = msg

         if value is None:
            return True # end command

         if type(value) == float:
            self.angle = qad_utils.toRadians(value)
            return True # end command
         elif type(value) == QgsPointXY:
            if not self.allowPoints:
               return True
            # the point(s) indicated by this function must not alter lastpoint
            self.plugIn.setLastPoint(self.__prevLastPoint)

            if self.startPt is not None:
               self.angle = qad_utils.getAngleBy2Pts(self.startPt, value)
               return True # end command
            else:
               self.startPt = value
               # set the map tool
               self.getPointMapTool().setDrawMode(QadGetPointDrawModeEnum.ELASTIC_LINE)
               self.getPointMapTool().setStartPoint(self.startPt)
               prompt = QadMsg.translate("QAD", "Specify second point: ")
               # is preparing to wait for a point
               self.waitForPoint(prompt)
               self.step = 2

         return False

      # =========================================================================
      # RESPONSE TO THE REQUEST SECOND POINT OF THE CORNER (from step = 1)
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

         if qad_utils.ptNear(self.startPt, value):
            self.showMsg(QadMsg.translate("QAD", "\nThe points must be different."))
            # is preparing to wait for a point
            self.waitForPoint(QadMsg.translate("QAD", "Specify second point: "))
            return False
         else:
            self.angle = qad_utils.getAngleBy2Pts(self.startPt, value)
            return True # end command
