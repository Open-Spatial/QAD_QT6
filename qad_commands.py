# -*- coding: utf-8 -*-

"""
/***************************************************************************
 QAD Quantum Aided Design plugin

 class to manage commands

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
from qgis.PyQt.QtCore import QObject
from qgis.PyQt.QtWidgets import QMessageBox

import sys, traceback
from datetime import date

from .qad_maptool import QadMapTool, QadVirtualSelCommandClass, QadVirtualGripCommandsClass
from .qad_msg import QadMsg
from .qad_cmd_aliases import *
from .qad_variables import QadVariables

from .qad_getpoint import *
from .qad_utils import decriptPlainText, getQADPath, getMacAddress
from .qad_geometry_capture import QadGeometryCaptureResult
from .qad_scalar_capture import QadScalarCaptureCommand, QadScalarCaptureResult, scalar_input_mode
from .cmd.qad_generic_cmd import QadCommandClass
from .cmd.qad_id_cmd import QadIDCommandClass
from .cmd.qad_setcurrlayerbygraph_cmd import QadSETCURRLAYERBYGRAPHCommandClass, QadSETCURRUPDATEABLELAYERBYGRAPHCommandClass
from .cmd.qad_setvar_cmd import QadSETVARCommandClass
from .cmd.qad_pline_cmd import QadPLINECommandClass
from .cmd.qad_arc_cmd import QadARCCommandClass
from .cmd.qad_circle_cmd import QadCIRCLECommandClass
from .cmd.qad_dsettings_cmd import QadDSETTINGSCommandClass
from .cmd.qad_line_cmd import QadLINECommandClass
from .cmd.qad_erase_cmd import QadERASECommandClass
from .cmd.qad_mpolygon_cmd import QadMPOLYGONCommandClass
from .cmd.qad_mbuffer_cmd import QadMBUFFERCommandClass
from .cmd.qad_rotate_cmd import QadROTATECommandClass
from .cmd.qad_move_cmd import QadMOVECommandClass
from .cmd.qad_scale_cmd import QadSCALECommandClass
from .cmd.qad_copy_cmd import QadCOPYCommandClass
from .cmd.qad_offset_cmd import QadOFFSETCommandClass
from .cmd.qad_extend_cmd import QadEXTENDCommandClass
from .cmd.qad_trim_cmd import QadTRIMCommandClass
from .cmd.qad_rectangle_cmd import QadRECTANGLECommandClass
from .cmd.qad_mirror_cmd import QadMIRRORCommandClass
from .cmd.qad_undoredo_cmd import QadUNDOCommandClass, QadREDOCommandClass
from .cmd.qad_insert_cmd import QadINSERTCommandClass
from .cmd.qad_text_cmd import QadTEXTCommandClass
from .cmd.qad_stretch_cmd import QadSTRETCHCommandClass
from .cmd.qad_break_cmd import QadBREAKCommandClass
from .cmd.qad_pedit_cmd import QadPEDITCommandClass
from .cmd.qad_fillet_cmd import QadFILLETCommandClass
from .cmd.qad_polygon_cmd import QadPOLYGONCommandClass
from .cmd.qad_dim_cmd import QadDIMLINEARCommandClass, QadDIMALIGNEDCommandClass, QadDIMARCCommandClass, QadDIMRADIUSCommandClass
from .cmd.qad_dimstyle_cmd import QadDIMSTYLECommandClass
from .cmd.qad_lengthen_cmd import QadLENGTHENCommandClass
from .cmd.qad_help_cmd import QadHELPCommandClass, QadSUPPORTERSCommandClass
from .cmd.qad_options_cmd import QadOPTIONSCommandClass
from .cmd.qad_mapmpedit_cmd import QadMAPMPEDITCommandClass
from .cmd.qad_joindisjoin_cmd import QadJOINCommandClass, QadDISJOINCommandClass
from .cmd.qad_array_cmd import QadARRAYCommandClass, QadARRAYRECTCommandClass, QadARRAYPATHCommandClass, QadARRAYPOLARCommandClass
from .cmd.qad_divide_cmd import QadDIVIDECommandClass
from .cmd.qad_measure_cmd import QadMEASURECommandClass
from .cmd.qad_ellipse_cmd import QadELLIPSECommandClass


# Class that handles Qad commands
class QadCommandsClass():
   # when adding a new command you must
   # 1) add it to the __cmdObjs list in the __init__ function
   # 2) if the command can be called from the menu or toolbar, see the Qad::initGui function (qad.py)
   #    and remember to insert the icon into resources.qrc and recompile the resources
   # 3) add function to start the "run<command_name>Command" command

   def __init__(self, plugIn):
      self.plugIn = plugIn

      self.__cmdObjs = [] # internal list of command objects
      self.__cmdObjs.append(QadIDCommandClass(self.plugIn)) # ID
      self.__cmdObjs.append(QadSETVARCommandClass(self.plugIn)) # SETVAR
      self.__cmdObjs.append(QadPLINECommandClass(self.plugIn)) # PLINE
      self.__cmdObjs.append(QadSETCURRLAYERBYGRAPHCommandClass(self.plugIn))# SETCURRLAYERBYGRAPH
      self.__cmdObjs.append(QadSETCURRUPDATEABLELAYERBYGRAPHCommandClass(self.plugIn)) # SETCURRUPDATEABLELAYERBYGRAPH
      self.__cmdObjs.append(QadARCCommandClass(self.plugIn)) # ARC
      self.__cmdObjs.append(QadCIRCLECommandClass(self.plugIn)) # CIRCLE
      self.__cmdObjs.append(QadDSETTINGSCommandClass(self.plugIn)) # DSETTINGS
      self.__cmdObjs.append(QadLINECommandClass(self.plugIn)) # LINE
      self.__cmdObjs.append(QadERASECommandClass(self.plugIn)) # ERASE
      self.__cmdObjs.append(QadMPOLYGONCommandClass(self.plugIn)) # MPOLYGON
      self.__cmdObjs.append(QadMBUFFERCommandClass(self.plugIn)) # MBUFFER
      self.__cmdObjs.append(QadROTATECommandClass(self.plugIn)) # ROTATE
      self.__cmdObjs.append(QadMOVECommandClass(self.plugIn)) # MOVE
      self.__cmdObjs.append(QadSCALECommandClass(self.plugIn)) # SCALE
      self.__cmdObjs.append(QadCOPYCommandClass(self.plugIn)) # COPY
      self.__cmdObjs.append(QadOFFSETCommandClass(self.plugIn)) # OFFSET
      self.__cmdObjs.append(QadEXTENDCommandClass(self.plugIn)) # EXTEND
      self.__cmdObjs.append(QadTRIMCommandClass(self.plugIn)) # TRIM
      self.__cmdObjs.append(QadRECTANGLECommandClass(self.plugIn)) # RECTANGLE
      self.__cmdObjs.append(QadMIRRORCommandClass(self.plugIn)) # MIRROR
      self.__cmdObjs.append(QadUNDOCommandClass(self.plugIn)) # UNDO
      self.__cmdObjs.append(QadREDOCommandClass(self.plugIn)) # REDO
      self.__cmdObjs.append(QadINSERTCommandClass(self.plugIn)) # INSERT
      self.__cmdObjs.append(QadTEXTCommandClass(self.plugIn)) # TEXT
      self.__cmdObjs.append(QadSTRETCHCommandClass(self.plugIn)) # STRETCH
      self.__cmdObjs.append(QadBREAKCommandClass(self.plugIn)) # BREAK
      self.__cmdObjs.append(QadPEDITCommandClass(self.plugIn)) # PEDIT
      self.__cmdObjs.append(QadFILLETCommandClass(self.plugIn)) # FILLET
      self.__cmdObjs.append(QadPOLYGONCommandClass(self.plugIn)) # POLYGON
      self.__cmdObjs.append(QadDIMLINEARCommandClass(self.plugIn)) # DIMLINEAR
      self.__cmdObjs.append(QadDIMALIGNEDCommandClass(self.plugIn)) # DIMALIGNED
      self.__cmdObjs.append(QadDIMARCCommandClass(self.plugIn)) # DIMARC
      self.__cmdObjs.append(QadDIMRADIUSCommandClass(self.plugIn)) # DIMRADIUS
      self.__cmdObjs.append(QadDIMSTYLECommandClass(self.plugIn)) # DIMSTYLE
      self.__cmdObjs.append(QadHELPCommandClass(self.plugIn)) # HELP
      self.__cmdObjs.append(QadLENGTHENCommandClass(self.plugIn)) # LENGTHEN
      self.__cmdObjs.append(QadOPTIONSCommandClass(self.plugIn)) # OPTIONS
      self.__cmdObjs.append(QadMAPMPEDITCommandClass(self.plugIn)) # MAPMPEDIT
      self.__cmdObjs.append(QadJOINCommandClass(self.plugIn)) # JOIN
      self.__cmdObjs.append(QadDISJOINCommandClass(self.plugIn)) # DISJOIN
      self.__cmdObjs.append(QadARRAYCommandClass(self.plugIn)) # ARRAY
      self.__cmdObjs.append(QadARRAYRECTCommandClass(self.plugIn)) # ARRAYRECT
      self.__cmdObjs.append(QadARRAYPATHCommandClass(self.plugIn)) # ARRAYPATH
      self.__cmdObjs.append(QadARRAYPOLARCommandClass(self.plugIn)) # ARRAYPOLAR
      self.__cmdObjs.append(QadDIVIDECommandClass(self.plugIn)) # DIVIDE
      self.__cmdObjs.append(QadMEASURECommandClass(self.plugIn)) # MEASURE
      self.__cmdObjs.append(QadELLIPSECommandClass(self.plugIn)) # ELLIPSE
      self.__cmdObjs.append(QadSUPPORTERSCommandClass(self.plugIn)) # SUPPORTERS

      self.actualCommand = None  # Command in progress
      self.geometryCaptureCallback = None
      self.geometryCaptureCommandName = None
      self.geometryCaptureTargetWkbType = None
      self.scalarCaptureCallback = None
      self.scalarCaptureInputType = None

      # I discard aliases that have the same name as commands
      exceptionList = []
      for cmdObj in self.__cmdObjs:
         exceptionList.append(cmdObj.getName())
         exceptionList.append("_" + cmdObj.getEnglishName())

      # carico alias dei comandi
      self.commandAliases = QadCommandAliasesClass()
      self.commandAliases.load("", exceptionList)

      self.usedCmdNames = QadUsedCmdNamesClass()


   def isValidCommand(self, command):
      cmd = self.getCommandObj(command)
      if cmd:
         del cmd
         return True
      else:
         return False


   def isValidEnvVariable(self, variable):
      # check if it is a system variable
      if QadVariables.get(variable) is not None:
         return True
      else:
         return False


   def showCommandPrompt(self):
      if self.plugIn is not None:
         self.plugIn.showInputMsg() # displays standard prompt for command request

   def showMsg(self, msg, displayPromptAfterMsg = False):
      if self.plugIn is not None:
         self.plugIn.showMsg(msg, displayPromptAfterMsg)

   def showErr(self, err):
      if self.plugIn is not None:
         self.plugIn.showErr(err)


   # ============================================================================
   # getCommandObj
   # ============================================================================
   def getCommandObj(self, cmdName, useAlias = True):
      if cmdName is None:
         return None
      if cmdName == "":
         return None
      upperCommand = cmdName.upper()
      if upperCommand[0] == "_":
         englishName = True
         upperCommand = upperCommand[1:] # I skip the first character of "_"
      else:
         englishName = False

      for cmd in self.__cmdObjs:
         if englishName:
            if upperCommand == cmd.getEnglishName(): # in inglese
               return cmd.instantiateNewCmd()
         else:
            if upperCommand == cmd.getName(): # in lingua locale
               return cmd.instantiateNewCmd()

      if cmdName == "MACRO_RUNNER":
         return QadMacroRunnerCommandClass(self.plugIn)
      else:
         if useAlias:
            command = self.commandAliases.getCommandName(cmdName)
            return self.getCommandObj(command, False)
         else:
            return None


   # ============================================================================
   # getCommandNames
   # ============================================================================
   def getCommandNames(self):
      """ Return a list of pairs : [(<local cmd name>, <english cmd name>)...]"""
      cmdNames = []
      # I get the list of command names
      for cmd in self.__cmdObjs:
         cmdNames.append([cmd.getName(), cmd.getEnglishName]) # in lingua locale, in inglese
      # add the aliases
      for alias in self.commandAliases.getCommandAliasDict().keys():
         cmdNames.append([alias, alias])

      return cmdNames


   # ============================================================================
   # run
   # ============================================================================
   def run(self, command, param = None):
      try:
         # if there is an active command
         if self.actualCommand is not None:
            return

         if command != QadMsg.translate("Command_list", "SUPPORTERS"):
            if incrementDailyCmdCounter() > self.plugIn.maxDailyCmdCounter:
               if QMessageBox.question(None, "QAD", QadMsg.translate("QAD", "QAD lets you run 200 commands per day free of popups. Donations help us to fund software development, documentation, translation and bug-fixing efforts. Do you want to donate ?"), \
                                       QMessageBox.StandardButton.Yes, QMessageBox.StandardButton.No) == QMessageBox.StandardButton.Yes:
                  command = "_SUPPORTERS";
#                if QMessageBox.critical(None, "QAD", QadMsg.translate("QAD", "You have run out of daily commands available for this version of QAD, your reasonable donation will allow us to adapt the product to your needs. Do you want to donate ?"), \
#                                        QMessageBox.StandardButton.Yes, QMessageBox.StandardButton.No) == QMessageBox.StandardButton.Yes:
#                   command = "_SUPPORTERS";
#                else:
#                   return

         # exception for virtual command "QadVirtualSelCommandClass" which is not actually a command
         # but it is used to select objects when no command is active
         if command == "QadVirtualSelCommandClass":
            self.actualCommand = QadVirtualSelCommandClass(self.plugIn)
            # param is the current position of the mouse
            if self.actualCommand.run(False, param) == True: # command finished
               self.clearCommand()
            return

         # exception for virtual command "QadVirtualGripCommandsClass" which is not actually a command
         # but it is used to modify objects selected by grip points
         if command == "QadVirtualGripCommandsClass":
            self.actualCommand = QadVirtualGripCommandsClass(self.plugIn)
            # param is a list where:
            # the first element is the code of the command to execute
            # the second element is entitySetGripPoints
            # the third element is the current grip point
            self.actualCommand.entitySetGripPoints = param[1]
            self.actualCommand.basePt = param[2]
            self.actualCommand.initStartCommand(param[0])
            if self.actualCommand.run(False) == True: # command finished
               self.clearCommand()
            return

         self.actualCommand = self.getCommandObj(command)
         if self.actualCommand is None:
            # check if it is a system variable
            if QadVariables.get(command) is not None:
               self.showMsg("\n")
               # launch SETVAR command to set the variable
               args = [QadMsg.translate("Command_list", "SETVAR"), command]
               return self.runMacro(args)

            msg = QadMsg.translate("QAD", "\nInvalid command \"{0}\".")
            self.showErr(msg.format(command))
            return

         self.usedCmdNames.setUsed(command)
         self.plugIn.clearEntityGripPoints() # pulisco i grip points correnti
         if self.actualCommand.run() == True: # command finished
            self.clearCommand()

      except Exception as e:
         self.abortCommand("failed", str(e))
         displayError(e)

   def runGeometryCapture(self, command, callback, target_wkb_type = None, *, prompts = None, finish_on_point_count = None, selection_steps = None):
      try:
         if callback is None or callable(callback) == False:
            return False
         if self.actualCommand is not None:
            callback(QadGeometryCaptureResult(command, "failed", [], "Another QAD command is already active."))
            return False

         self.actualCommand = self.getCommandObj(command)
         if self.actualCommand is None:
            callback(QadGeometryCaptureResult(command, "failed", [], "Invalid command \"{0}\".".format(command)))
            return False
         if self.actualCommand.getEnglishName() not in ("LINE", "PLINE", "MPOLYGON"):
            callback(QadGeometryCaptureResult(command, "failed", [], "Geometry capture supports LINE, PLINE and MPOLYGON only."))
            self.actualCommand = None
            return False

         self.geometryCaptureCallback = callback
         self.geometryCaptureCommandName = self.actualCommand.getEnglishName()
         self.geometryCaptureTargetWkbType = target_wkb_type
         self.actualCommand.virtualCmd = True
         set_prompts = getattr(self.actualCommand, "setCapturePrompts", None)
         if callable(set_prompts):
            set_prompts(prompts)
         set_finish_count = getattr(self.actualCommand, "setCaptureFinishOnPointCount", None)
         if callable(set_finish_count):
            set_finish_count(finish_on_point_count)
         set_selection_steps = getattr(self.actualCommand, "setCaptureSelectionSteps", None)
         if callable(set_selection_steps):
            set_selection_steps(selection_steps)
         self.usedCmdNames.setUsed(command)
         self.plugIn.clearEntityGripPoints()
         if self.actualCommand.run() == True:
            self.clearCommand()
         return True

      except Exception as e:
         self.abortCommand("failed", str(e))
         displayError(e)
         return False


   def runScalarCapture(self, callback, *, prompt, input_type = "string", default = None, keywords = None, allow_null = False, allow_zero = True, allow_negative = True, allow_positive = True):
      try:
         if callback is None or callable(callback) == False:
            return False
         normalized_type = str(input_type or "").strip().lower()
         supported_types = (
            "string",
            "integer",
            "float",
            "keyword",
            "point",
            "point_or_keyword",
            "point_or_distance",
            "point_or_angle_or_keyword",
         )
         if normalized_type not in supported_types:
            callback(QadScalarCaptureResult(normalized_type, "failed", None, "Unsupported scalar input type."))
            return False
         clean_prompt = str(prompt or "")
         if clean_prompt.strip() == "":
            callback(QadScalarCaptureResult(normalized_type, "failed", None, "A scalar input prompt is required."))
            return False
         if self.actualCommand is not None:
            callback(QadScalarCaptureResult(normalized_type, "failed", None, "Another QAD command is already active."))
            return False

         if keywords is None:
            keyword_text = ""
         elif isinstance(keywords, str):
            keyword_text = keywords
         else:
            keyword_text = "/".join(str(value) for value in keywords)
         keyword_types = ("keyword", "point_or_keyword", "point_or_angle_or_keyword")
         if normalized_type in keyword_types and keyword_text.strip() == "":
            callback(QadScalarCaptureResult(normalized_type, "failed", None, "Keyword input requires keywords."))
            return False

         input_mode = scalar_input_mode(
            allow_null = bool(allow_null),
            allow_zero = bool(allow_zero),
            allow_negative = bool(allow_negative),
            allow_positive = bool(allow_positive),
         )
         self.actualCommand = QadScalarCaptureCommand(
            self.plugIn,
            prompt = clean_prompt,
            input_type = normalized_type,
            default = default,
            keywords = keyword_text,
            input_mode = input_mode,
            allow_null = bool(allow_null),
         )
         self.scalarCaptureCallback = callback
         self.scalarCaptureInputType = normalized_type
         self.usedCmdNames.setUsed("MUNSYSQ_SCALAR")
         self.plugIn.clearEntityGripPoints()
         if self.actualCommand.run() == True:
            self.clearCommand()
         return True

      except Exception as e:
         self.abortCommand("failed", str(e))
         displayError(e)
         return False


   # ============================================================================
   # runMacro
   # ============================================================================
   def runMacro(self, args):
      try:
         # if there is no active command
         if self.actualCommand is not None:
            return

         if args[0] != QadMsg.translate("Command_list", "SUPPORTERS"):
            if incrementDailyCmdCounter() > self.plugIn.maxDailyCmdCounter:
               if QMessageBox.question(None, "QAD", QadMsg.translate("QAD", "QAD lets you run 200 commands per day free of popups. Donations help us to fund software development, documentation, translation and bug-fixing efforts. Do you want to donate ?"), \
                                       QMessageBox.StandardButton.Yes, QMessageBox.StandardButton.No) == QMessageBox.StandardButton.Yes:
                  args[0] = "_SUPPORTERS";
#                if QMessageBox.critical(None, "QAD", QadMsg.translate("QAD", "You have run out of daily commands available for this version of QAD, your reasonable donation will allow us to adapt the product to your needs. Do you want to donate ?"), \
#                                        QMessageBox.StandardButton.Yes, QMessageBox.StandardButton.No) == QMessageBox.StandardButton.Yes:
#                   args[0] = "_SUPPORTERS";
#                else:
#                   return

         self.actualCommand = self.getCommandObj("MACRO_RUNNER")
         if self.actualCommand is None:
            msg = QadMsg.translate("QAD", "\nInvalid command \"{0}\".")
            self.showErr(msg.format(command))
            return

         self.plugIn.clearEntityGripPoints() # pulisco i grip points correnti
         self.actualCommand.setCmdAndOptionsToRun(args)

         self.showMsg(args[0]) # I display the command name in macro
         if self.actualCommand.run() == True: # command finished
            self.clearCommand()

      except Exception as e:
         self.abortCommand("failed", str(e))
         displayError(e)


   # ============================================================================
   # continueCommandFromMapTool
   # ============================================================================
   def continueCommandFromMapTool(self):
      try:
         # if there is no active command
         if self.actualCommand is None:
            return
         msg = None
         # if the right mouse button was pressed I evaluate what was inserted in the text window
         if self.actualCommand.getPointMapTool().rightButton == True:
            msg = self.actualCommand.getCurrMsgFromTxtWindow()
            if (msg is not None) and len(msg) > 0:
               self.actualCommand.showEvaluateMsg()
            else:
               if self.actualCommand.run(True) == True: # command finished
                  self.clearCommand()
         else:
            if self.actualCommand.run(True) == True: # command finished
               self.clearCommand()

      except Exception as e:
         self.abortCommand("failed", str(e))
         displayError(e)


   # ============================================================================
   # continueCommandFromTextWindow
   # ============================================================================
   def continueCommandFromTextWindow(self, msg):
      try:
         # if there is no active command
         if self.actualCommand is None:
            return
         if self.actualCommand.run(False, msg) == True: # command finished
            self.clearCommand()

      except Exception as e:
         self.abortCommand()
         displayError(e)


   # ============================================================================
   # abortCommand
   # ============================================================================
   def abortCommand(self, geometry_capture_status = "cancelled", geometry_capture_message = ""):
      # if there is no active command
      if self.actualCommand is None:
         self.emitGeometryCaptureResult(geometry_capture_status, geometry_capture_message)
         self.emitScalarCaptureResult(geometry_capture_status, geometry_capture_message)
         self.showCommandPrompt() # displays standard prompt for command request
         self.plugIn.setStandardMapTool()
         self.plugIn.getCurrentMapTool()
      else:
         self.showMsg(QadMsg.translate("QAD", "*Canceled*"))
         self.clearCommand(geometry_capture_status, geometry_capture_message)
         # I clean the selected entities and the current grip points
         self.plugIn.clearCurrentObjsSelection()


   # ============================================================================
   # clearCommand
   # ============================================================================
   def clearCommand(self, geometry_capture_status = "completed", geometry_capture_message = ""):
      if self.actualCommand is None:
         self.emitGeometryCaptureResult(geometry_capture_status, geometry_capture_message)
         self.emitScalarCaptureResult(geometry_capture_status, geometry_capture_message)
         return

      # exception for virtual command "QadVirtualGripCommandsClass" which is not actually a command
      # but it is used to modify objects selected by grip points
      if self.actualCommand.getName() == "QadVirtualGripCommandsClass":
         # ridisegno i grip point nelle nuove posizioni resettando quelli selezionati
         self.plugIn.tool.clearEntityGripPoints()
         self.plugIn.tool.refreshEntityGripPoints()
      else:
         # exception for virtual command "QadVirtualSelCommandClass" which is not actually a command
         # but it is used to select objects when no command is active
         if self.actualCommand.getName() != "QadVirtualSelCommandClass":
            qad_utils.deselectAll(self.plugIn.canvas.layers())

      self.emitGeometryCaptureResult(geometry_capture_status, geometry_capture_message, self.actualCommand)
      self.emitScalarCaptureResult(geometry_capture_status, geometry_capture_message, self.actualCommand)

      del self.actualCommand
      self.actualCommand = None
      self.plugIn.setStandardMapTool()
      self.plugIn.tool.getDynamicInput().show(False)
      self.showCommandPrompt() # displays standard prompt for command request

   def emitGeometryCaptureResult(self, status, message = "", command = None):
      callback = self.geometryCaptureCallback
      if callback is None:
         return

      self.geometryCaptureCallback = None
      command_name = self.geometryCaptureCommandName or ""
      target_wkb_type = self.geometryCaptureTargetWkbType
      self.geometryCaptureCommandName = None
      self.geometryCaptureTargetWkbType = None

      geometries = []
      selections = []
      final_status = status
      final_message = message or ""
      if final_status == "completed" and command is not None:
         try:
            get_geometries = getattr(command, "capturedGeometries", None)
            if callable(get_geometries):
               geometries = [geom for geom in get_geometries(target_wkb_type) if geom is not None]
            get_selections = getattr(command, "capturedSelections", None)
            if callable(get_selections):
               selections = [selection for selection in get_selections() if selection is not None]
         except Exception as ex:
            final_status = "failed"
            geometries = []
            selections = []
            final_message = str(ex)
      if final_status == "completed" and len(geometries) == 0 and len(selections) == 0:
         final_status = "cancelled"
      try:
         callback(QadGeometryCaptureResult(command_name, final_status, geometries, final_message, selections))
      except Exception:
         pass

   def emitScalarCaptureResult(self, status, message = "", command = None):
      callback = self.scalarCaptureCallback
      if callback is None:
         return

      self.scalarCaptureCallback = None
      input_type = self.scalarCaptureInputType or ""
      self.scalarCaptureInputType = None
      value = None
      final_status = status
      final_message = message or ""
      if final_status == "completed" and command is not None:
         try:
            get_error = getattr(command, "scalarCaptureError", None)
            if callable(get_error):
               final_message = str(get_error() or "")
            if final_message:
               final_status = "failed"
            else:
               get_value = getattr(command, "capturedScalarValue", None)
               if callable(get_value):
                  value = get_value()
               if value is None and getattr(command, "allowNull", False) == False:
                  final_status = "cancelled"
         except Exception as ex:
            final_status = "failed"
            value = None
            final_message = str(ex)
      try:
         callback(QadScalarCaptureResult(input_type, final_status, value, final_message))
      except Exception:
         pass


   # ============================================================================
   # getActualCommandPointMapTool
   # ============================================================================
   def getActualCommandPointMapTool(self):
      # if there is no active command
      if self.actualCommand is None:
         return None
      # if there is no map tool of the current command
      if self.actualCommand.getPointMapTool() is None:
         return None
      # if the map tool of the current command is not active
      if self.plugIn.canvas.mapTool() != self.actualCommand.getPointMapTool():
         self.actualCommand.setMapTool(self.actualCommand.getPointMapTool())
      return self.actualCommand.getPointMapTool()


   # ============================================================================
   # forceCommandMapToolSnapTypeOnce
   # ============================================================================
   def forceCommandMapToolSnapTypeOnce(self, snapType, snapParams = None):
      pointMapTool = self.getActualCommandPointMapTool()
      if pointMapTool is None:
         return
      pointMapTool.forceSnapTypeOnce(snapType, snapParams)


   # ============================================================================
   # forceCommandMapToolM2P
   # ============================================================================
   def forceCommandMapToolM2P(self):
      pointMapTool = self.getActualCommandPointMapTool()
      if pointMapTool is None:
         return
      pointMapTool.forceM2P()


   # ============================================================================
   # getCurrenPointFromCommandMapTool
   # ============================================================================
   def getCurrenPointFromCommandMapTool(self):
      pointMapTool = self.getActualCommandPointMapTool()
      if pointMapTool is None:
         return None
      return pointMapTool.tmpPoint


   # ============================================================================
   # refreshCommandMapToolSnapType
   # ============================================================================
   def refreshCommandMapToolSnapType(self):
      pointMapTool = self.getActualCommandPointMapTool()
      if pointMapTool is None:
         return
      pointMapTool.refreshSnapType()


   # ============================================================================
   # refreshCommandMapToolOrthoMode
   # ============================================================================
   def refreshCommandMapToolOrthoMode(self):
      pointMapTool = self.getActualCommandPointMapTool()
      if pointMapTool is None:
         return
      pointMapTool.refreshOrthoMode()


   # ============================================================================
   # refreshCommandMapToolAutoSnap
   # ============================================================================
   def refreshCommandMapToolAutoSnap(self):
      pointMapTool = self.getActualCommandPointMapTool()
      if pointMapTool is None:
         return
      pointMapTool.refreshAutoSnap()


   # ============================================================================
   # refreshCommandMapToolDynamicInput
   # ============================================================================
   def refreshCommandMapToolDynamicInput(self):
      self.plugIn.tool.getDynamicInput().refreshOnEnvVariables()

      pointMapTool = self.getActualCommandPointMapTool()
      if pointMapTool is not None:
         pointMapTool.getDynamicInput().refreshOnEnvVariables()
         if pointMapTool.getDynamicInput().isActive() == False:
            pointMapTool.getDynamicInput().show(False)
         else:
            pointMapTool.getDynamicInput().show(True)
      else:
         if self.plugIn.tool.getDynamicInput().isActive() == False:
            self.plugIn.tool.getDynamicInput().show(False)
         else:
            if self.plugIn.tool.getDynamicInput().resStr != "": # only if it already provided a result
               self.plugIn.tool.getDynamicInput().show(True)


   # ============================================================================
   # getMoreUsedCmd
   # ============================================================================
   def getMoreUsedCmd(self, filter):
      upperFilter = filter.upper()
      cmdName, qty = self.usedCmdNames.getMoreUsed(upperFilter)
      if cmdName == "": # no command
         if upperFilter[0] == "_":
            englishName = True
            upperFilter = upperFilter[1:] # I skip the first character of "_"
         else:
            englishName = False

         for cmd in self.__cmdObjs:
            if englishName:
               if cmd.getEnglishName().startswith(upperFilter): # in inglese
                  return cmd.getEnglishName(), 0
            else:
               if cmd.getName().startswith(upperFilter): # in lingua locale
                  return cmd.getName(), 0
      return cmdName, 0


# ===============================================================================
# QadMacroRunnerCommandClass
# ===============================================================================
class QadMacroRunnerCommandClass(QadCommandClass):
   # Class that manages the execution of other commands

   def instantiateNewCmd(self):
      """instantiates a new command of the same type"""
      return QadMacroRunnerCommandClass(self.plugIn)

   def getName(self):
      if self.command is None:
         return "MACRO_RUNNER"
      else:
         return self.command.getName()

   def getEnglishName(self):
      return "MACRO_RUNNER"

   def connectQAction(self, action):
      action.triggered.connect(self.plugIn.runREDOCommand)

   def __init__(self, plugIn):
      QadCommandClass.__init__(self, plugIn)
      self.command = None
      self.args = [] # list of topics
      self.argsIndex = -1

   def __del__(self):
      QadCommandClass.__del__(self)
      if self.command is not None:
         del self.command

   def getPointMapTool(self, drawMode = QadGetPointDrawModeEnum.NONE):
      if self.command is not None:
         return self.command.getPointMapTool(drawMode)
      else:
         return QadCommandClass.getPointMapTool(self, drawMode)


   def getCurrentContextualMenu(self):
      if self.command is None:
         return None
      else:
         return self.command.getCurrentContextualMenu()


   def setCmdAndOptionsToRun(self, CmdAndArglist):
      # first element of the list = command name
      # the other elements are the arguments of the command None = user input
      cmdName = CmdAndArglist[0]
      self.args = CmdAndArglist[1:] # I copy the list skipping the first element

      self.command = self.plugIn.getCommandObj(cmdName)

      if self.command is None:
         msg = QadMsg.translate("QAD", "\nInvalid command \"{0}\".")
         self.showErr(msg.format(command))
         return False
      self.plugIn.updateCmdsHistory(cmdName)
      return True


   def run(self, msgMapTool = False, msg = None):

      if self.command.run(msgMapTool, msg) == True:
         return True

      # if the previous input was valid
      if self.command.isValidPreviousInput == True:
         # to the command I pass the next option
         self.argsIndex = self.argsIndex + 1
         if self.argsIndex < len(self.args):
            arg = self.args[self.argsIndex]
            if arg is not None:
               self.showEvaluateMsg(arg)

      return False


# ===============================================================================
# QadUsedCmdNamesClass used to count how many times commands have been used
# ===============================================================================


class QadUsedCmdNamesClass():
   def __init__(self):
      self.__nUsedCmdNames = [] # internal list of items composed of (command name or alias, number of times it has been used)

   def __del__(self):
      del self.__nUsedCmdNames[:]


   def setUsed(self, cmdName):
      uName = cmdName.upper()
      for _cmdName in self.__nUsedCmdNames:
         if _cmdName[0] == uName:
            _cmdName[1] = _cmdName[1] + 1
            return _cmdName[1]

      self.__nUsedCmdNames.append([uName, 1])
      return 1


   def getUsed(self, cmdName):
      uName = cmdName.upper()
      for _cmdName in self.__nUsedCmdNames:
         if _cmdName[0] == uName:
            return _cmdName[1]

      return 0

   def getMoreUsed(self, filter):
      moreUsedCmd = ""
      nUsedCmd = 0
      for _cmdName in self.__nUsedCmdNames:
         if _cmdName[0].startswith(filter):
            if _cmdName[1] > nUsedCmd:
               moreUsedCmd = _cmdName[0]
               nUsedCmd = _cmdName[1]

      return moreUsedCmd, nUsedCmd


def displayError(exception = None):
   exc_type, exc_value, exc_traceback = sys.exc_info()
   format_exception = traceback.format_exception(exc_type, exc_value, exc_traceback)
   stk = ""
   for s in format_exception:
      if s != "Traceback (most recent call last):\n":
         stk = s + stk
   if exception is not None and exception.__doc__ is not None:
      stk = exception.__doc__ + "\n" + stk
   stk = QadMsg.translate("QAD", "Well, this is embarrassing !\n\n") + stk
   QMessageBox.critical(None, "QAD", stk)


def incrementDailyCmdCounter():
   key = '/qgis/digitizing/qad_daily_cmd_counter'
   today = date.today().strftime('%Y-%m-%d')
   value = QSettings().value(key, today + ";0")

   if type(value) != str:
      QSettings().setValue(key, today + ";1")
      return 1

   res = value.split(";")
   if len(res) != 2:
      QSettings().setValue(key, today + ";1")
      return 1

   if res[0] != today:
      QSettings().setValue(key, today + ";1")
      return 1

   n = qad_utils.str2int(res[1])
   if n is None:
      n = 0

   n = n + 1
   QSettings().setValue(key, today + ";" + str(n))
   return n


def getMaxDailyCmdCounter():
   try:
      path = getQADPath() + "/" + "auth.ini"
      f = open(path, "r")
      line = f.readline()
      f.close()
      if decriptPlainText(line) == getMacAddress():
         return 999999
   except:
      pass

   return 200
