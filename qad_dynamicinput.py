# -*- coding: utf-8 -*-
"""
/***************************************************************************
 QAD Quantum Aided Design plugin

 class to manage dynamic input

                              -------------------
        begin                : 2017-07-27
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


from qgis.core import *
from qgis.gui import *

from qgis.PyQt.QtCore import Qt, QTimer, QPoint
from qgis.PyQt.QtGui import QColor, QFontMetrics, QTextCursor, QIcon, QPixmap
from qgis.PyQt.QtWidgets import QTextEdit, QSizePolicy, QApplication, QLabel, QWidget

import math

from . import qad_utils
from .qad_arc import QadArc
from .qad_entity import QadEntity
from .qad_grip import QadGripPointTypeEnum, QadEntityGripPoint
from .qad_msg import QadMsg
from .qad_rubberband import createRubberBand
from .qad_snapper import *
from .qad_textwindow import QadCmdSuggestWindow, QadInputTypeEnum, QadInputModeEnum
from .qad_variables import *
from .qad_variables import QadVariables, QadINPUTSEARCHOPTIONSEnum
from .qad_vertexmarker import *
from .qad_dim import QadDimStyles


# ===============================================================================
# QadDynamicInputContextEnum class.
# ===============================================================================
class QadDynamicInputContextEnum():
   NONE               = 0
   COMMAND            = 1   # request for a command
   EDIT               = 2   # request for editing


# ===============================================================================
# QadDynamicInputEditEnum class.
# ===============================================================================
class QadDynamicInputEditEnum(): # see initGui which declares a vector as long as the values of QadDynamicInputEditEnum
   CMD_LINE_EDIT        = 0 # used to enter a command
   PROMPT_EDIT          = 1 # used for messages and command option selection
   EDIT                 = 2 # used for generic request of a value (e.g. radius, scale, rotation)
   EDIT_X               = 3 # used for X coordinate
   EDIT_Y               = 4 # used for Y coordinate
   EDIT_Z               = 5 # used for Z coordinate
   # used for distance from the previous point if segment, used for radius length at the final point of the previous part if arc
   # or radius length at the midpoint if the previous and following part are the same arc
   EDIT_DIST_PREV_PT    = 6
   # used for distance relative to the previous position of the same point in the direction from the previous point if segment
   # used for radius length at the starting point of the previous part if arc
   EDIT_REL_DIST_PREV_PT = 7
   # used for angle from previous point if segment, used for arc angle at the final point of previous part if arc
   EDIT_ANG_PREV_PT     = 8
   # used for angle relative to angle from previous point if segment
   # used for total arc angle if previous and following part are the same arc
   EDIT_REL_ANG_PREV_PT = 9
   # used for distance to next point if segment,
   # used for radius length at the starting point of the next part if arc
   EDIT_DIST_NEXT_PT    = 10
   # used for distance relative to the previous position of the same point in the direction from the next point if segment
   # used for radius length at the end point of the next part if arc
   EDIT_REL_DIST_NEXT_PT = 11
   EDIT_ANG_NEXT_PT     = 12 # used for angle from next point, used for arc angle at start point of next part
   EDIT_REL_ANG_NEXT_PT = 13 # used for angle relative to angle from next point if segment
   EDIT_SYMBOL_COORD_TYPE = 14 # used to indicate whether absolute "#" or relative "@" coordinate


# each QadDynamicInputEdit is managed by QadDynamicEditInput functions:
# initGui, setFocus, setNextCurrentEdit, setPrevCurrentEdit, show, mouseMoveEvent, moveCtrls


# ===============================================================================
# QadDynamicEdit
# ===============================================================================
class QadDynamicEdit(QTextEdit):
#    """
#    Class that handles dynamic input in a QTextEdit
#    """

   def __init__(self, QadDynamicInputObj):
      QTextEdit.__init__(self, QadDynamicInputObj.canvas)
      self.QadDynamicInputObj = QadDynamicInputObj
      self.plugIn = QadDynamicInputObj.plugIn
      self.canvas = QadDynamicInputObj.canvas

      self.font_size = 8 + QadVariables.get(QadMsg.translate("Environment variables", "TOOLTIPSIZE"))
      height = self.font_size + 15

      self.setTextInteractionFlags(Qt.TextEditorInteraction)
      self.setMinimumSize(height, height)
      self.setMaximumHeight(height)
      self.setUndoRedoEnabled(False)
      self.setAcceptRichText(False)
      self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
      self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
      self.error = False # indicates if the value contained in the edit is incorrect
      self.lockedPos = False # indicates whether the edit position is locked


   # ============================================================================
   # focusInEvent
   # ============================================================================
   def focusInEvent(self, e):
      pass


   # ============================================================================
   # reset
   # ============================================================================
   def reset(self):
      self.showMsg("")
      self.error = False
      self.lockedPos = False


   # ============================================================================
   # setColors
   # ============================================================================
   def setColors(self, foregroundColor = None, backGroundColor = None, borderColor = None, \
                 selectionColor = None, selectionBackGroundColor = None, opacity = 100):
      # if the colors are None then they are not altered
      # special case for borderColor = "" is not drawn
      # opacity = 0-100
      oldFmt = self.styleSheet().split(";")
      fmt = "rgba({0},{1},{2},{3}%)"

      if foregroundColor is not None:
         c = QColor(foregroundColor)
         rgbStrForeColor = "color: " + fmt.format(str(c.red()), str(c.green()), str(c.blue()), str(opacity)) + ";"
      else:
         rgbStrForeColor = ""
         for f in oldFmt:
            if f.find("color:") == 0:
               rgbStrForeColor = f + ";"
               break

      if backGroundColor is not None:
         c = QColor(backGroundColor)
         rgbStrBackColor = "background-color: " + fmt.format(str(c.red()), str(c.green()), str(c.blue()), str(opacity)) + ";"
      else:
         rgbStrBackColor = ""
         for f in oldFmt:
            if f.find("background-color:") == 0:
               rgbStrBackColor = f + ";"
               break

      # if it is in error state the border must be red 2 pixels wide
      if self.error:
         c = QColor(Qt.GlobalColor.red)
         rgbStrBorderColor = "border-color: " + fmt.format(str(c.red()), str(c.green()), str(c.blue()), str(opacity)) + ";"
         fmtBorder = "border:2px;border-style:solid;"
      else:
         if borderColor is not None:
            if borderColor == "": # without border
               rgbStrBorderColor = ""
               fmtBorder = "border:0px;border-style:solid;"
            else:
               c = QColor(borderColor)
               rgbStrBorderColor = "border-color: " + fmt.format(str(c.red()), str(c.green()), str(c.blue()), str(opacity)) + ";"
               fmtBorder = "border:1px;border-style:solid;"
         else:
            rgbStrBorderColor = ""
            fmtBorder = ""
            for f in oldFmt:
               if f.find("border-color:") == 0:
                  rgbStrBorderColor = f + ";"
               elif f.find("border:") == 0:
                  fmtBorder = fmtBorder + f + ";"
               elif f.find("border-style:") == 0:
                  fmtBorder = fmtBorder + f + ";"

      if selectionColor is not None:
         c = QColor(selectionColor)
         rgbStrSelectionColor = "selection-color: " + fmt.format(str(c.red()), str(c.green()), str(c.blue()), str(opacity)) + ";"
      else:
         rgbStrSelectionColor = ""
         for f in oldFmt:
            if f.find("selection-color:") == 0:
               rgbStrSelectionColor = f + ";"
               break

      if selectionBackGroundColor is not None:
         c = QColor(selectionBackGroundColor)
         rgbStrSelectionBackColor = "selection-background-color: " + fmt.format(str(c.red()), str(c.green()), str(c.blue()), str(opacity)) + ";"
      else:
         rgbStrSelectionBackColor = ""
         for f in oldFmt:
            if f.find("selection-background-color:") == 0:
               rgbStrSelectionBackColor = f + ";"
               break

      fmt = rgbStrForeColor + \
            rgbStrBackColor + \
            fmtBorder + \
            rgbStrBorderColor + \
            rgbStrSelectionColor + \
            rgbStrSelectionBackColor + \
            "font-size: " + str(self.font_size) + "pt;"

      self.setStyleSheet(fmt)


   def refreshWidth(self, updateCtrlsPos = True):
      fm = QFontMetrics(self.currentFont())
      boundingRect = fm.boundingRect(self.toPlainText())
      width = int(boundingRect.width() * 1.2) + 5
      height = boundingRect.height()

      canvasRect = self.canvas.rect()
      if width > canvasRect.width():
         width = canvasRect.width()

      self.resize(width, height)
      if updateCtrlsPos: self.QadDynamicInputObj.moveCtrls()


   # ============================================================================
   # selectAllText
   # ============================================================================
   def selectAllText(self):
      # I select all the text
      cursor = self.textCursor()
      cursor.movePosition(QTextCursor.End, QTextCursor.MoveAnchor)
      cursor.movePosition(QTextCursor.Start, QTextCursor.KeepAnchor)
      self.setTextCursor(cursor)


   # ============================================================================
   # showMsg
   # ============================================================================
   def showMsg(self, msg, dummy1 = False, dummy2 = False, updateCtrlsPos = True):
      self.error = False
      cursor = self.textCursor()
      sep = msg.rfind("\n")
      if sep >= 0:
         newMsg = msg[sep + 1:]
         cursor.movePosition(QTextCursor.Start, QTextCursor.MoveAnchor)
         cursor.movePosition(QTextCursor.End, QTextCursor.KeepAnchor)
      else:
         newMsg = msg
         cursor.movePosition(QTextCursor.Start, QTextCursor.MoveAnchor)
         cursor.movePosition(QTextCursor.End, QTextCursor.KeepAnchor)

      self.setTextCursor(cursor)
      self.insertPlainText(newMsg)
      self.refreshWidth(updateCtrlsPos)


   # ============================================================================
   # removeItems
   # ============================================================================
   def removeItems(self):
      pass


# ===============================================================================
# QadDynamicInputCmdLineEdit
# ===============================================================================
class QadDynamicInputCmdLineEdit(QadDynamicEdit):
#    """
#    Class that handles command line-only dynamic input
#    """

   def __init__(self, QadDynamicInputObj):
      QadDynamicEdit.__init__(self, QadDynamicInputObj)
      self.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)

      self.historyIndex = 0

      self.timerForCmdSuggestWindow = QTimer()
      self.timerForCmdSuggestWindow.setSingleShot(True)
      self.timerForCmdAutoComplete = QTimer()
      self.timerForCmdAutoComplete.setSingleShot(True)

      self.infoCmds = []
      self.infoVars = []

      self.cmdSuggestWindow = None

      foregroundColor = QColor(QadVariables.get(QadMsg.translate("Environment variables", "CMDLINEFORECOLOR")))
      backGroundColor = QColor(QadVariables.get(QadMsg.translate("Environment variables", "CMDLINEBACKCOLOR")))
      borderColor = QColor(QadVariables.get(QadMsg.translate("Environment variables", "DYNEDITBORDERCOLOR")))
      opacity = 100 - QadVariables.get(QadMsg.translate("Environment variables", "TOOLTIPTRANSPARENCY"))
      self.setColors(foregroundColor, backGroundColor, borderColor, backGroundColor, foregroundColor, opacity)
      self.show(False)


   def initCmdVarsList(self):
      # list composed of elements with:
      # <command local name>, <command English name>, <icon>, <notes>
      self.infoCmds = []
      for cmdName in self.plugIn.getCommandNames():
         cmd = self.plugIn.getCommandObj(cmdName[0])
         if cmd is not None:
            self.infoCmds.append([cmdName[0], cmd.getEnglishName(), cmd.getIcon(), cmd.getNote()])

      # create the window for suggesting environment variables
      # list composed of elements with:
      # <variable name>, "", <icon>, <notes>
      self.infoVars = []
      icon = QIcon(":/plugins/qad/icons/variable.svg")
      for varName in QadVariables.getVarNames():
         var = QadVariables.getVariable(varName)
         self.infoVars.append([varName, "", icon, var.descr])


   def show(self, mode):
      if mode == False:
         self.timerForCmdAutoComplete.stop()
         self.lockedPos = False
         self.showCmdSuggestWindow(False) # hide suggestion window
         QTextEdit.setVisible(self, False)
      else:
#          if self.isVisible() == False:
#             self.showMsg("")
         QTextEdit.setVisible(self, True)
         self.setFocus()


   # ============================================================================
   # showMsg
   # ============================================================================
   def showMsg(self, msg, dummy1 = False, dummy2 = False, updateCtrlsPos = True):
      # the showMsg function is used by showMsg(self, cmd) in the QadCmdSuggestWindow class
      # which communicates with both QadEdit and QadDynamicInputCmdLineEdit
      # for compatibility with QadEdit's showMsg I have to add two dummy parameters (dummy, dummy2)
      QadDynamicEdit.showMsg(self, msg, dummy1, dummy2, updateCtrlsPos)


   # ============================================================================
   # showEvaluateMsg
   # ============================================================================
   def showEvaluateMsg(self, msg, append = False): # for compatibility with QadCmdSuggestListView.mouseReleaseEvent
      return self.QadDynamicInputObj.showEvaluateMsg(msg)


   # ============================================================================
   # showCmdSuggestWindow
   # ============================================================================
   def showCmdSuggestWindow(self, mode = True, filter = ""):
      if mode == False: # if I turn off the window
         self.timerForCmdSuggestWindow.stop()

      inputSearchOptions = QadVariables.get(QadMsg.translate("Environment variables", "INPUTSEARCHOPTIONS"))
      # inputSearcOptions & QadINPUTSEARCHOPTIONSEnum.ON = Turns on all automated keyboard features when typing at the Command prompt
      # inputSearcOptions & QadINPUTSEARCHOPTIONSEnum.DISPLAY_LIST = Displays a list of suggestions as keystrokes are entered
      if (inputSearchOptions & QadINPUTSEARCHOPTIONSEnum.ON and inputSearchOptions & QadINPUTSEARCHOPTIONSEnum.DISPLAY_LIST) and \
          mode == True:
         if self.cmdSuggestWindow is None:
            # create the command suggestion window
            self.initCmdVarsList()
            self.cmdSuggestWindow = QadCmdSuggestWindow(self.canvas, self, self.infoCmds, self.infoVars)
            self.cmdSuggestWindow.initGui()

         if self.cmdSuggestWindow.setFilter(filter) == 0:
            self.lockedPos = False;
            self.cmdSuggestWindow.show(False)
            return

         dataHeight = self.cmdSuggestWindow.getDataHeight()
         if dataHeight > 0:
            self.cmdSuggestWindow.cmdNamesListView.setMinimumHeight(self.cmdSuggestWindow.cmdNamesListView.sizeHintForRow(0))

         dataWidth = 200

         # I get the position of the top left corner of the QTextEdit relative to its parent
         editRect = self.geometry()
         ptUp = self.mapToGlobal(QPoint(0, 0))

         spaceUp = ptUp.y() if ptUp.y() - dataHeight < 0 else dataHeight

         ptDown = QPoint(ptUp.x(), ptUp.y() + editRect.height())
         desktopRect = qad_utils.getScreenGeometry(self, ptUp)
         spaceDown = desktopRect.height() - ptDown.y() if ptDown.y() + dataHeight > desktopRect.height() else dataHeight

         # check if there is more space above or below the window
         if spaceUp > spaceDown:
            pt = QPoint(ptUp.x(), ptUp.y() - spaceUp)
            dataHeight = spaceUp
         else:
            pt = QPoint(ptDown.x(), ptDown.y())
            dataHeight = spaceDown

         if pt.x() + dataWidth > desktopRect.width(): # if it goes beyond the right limit
            if desktopRect.width() - dataWidth < 0: # if even by moving the window to the left it projects to the left
               pt.setX(0)
               dataWidth = desktopRect.width()
            else:
               pt.setX(desktopRect.width() - dataWidth)

         self.cmdSuggestWindow.move(pt)
         self.cmdSuggestWindow.resize(dataWidth, dataHeight)

         self.cmdSuggestWindow.show(True)
         self.lockedPos = True # when the suggestion window is open the position freezes
      else:
         if self.cmdSuggestWindow is not None:
            self.lockedPos = False
            self.cmdSuggestWindow.show(False)


   def showCmdAutoComplete(self, filter = ""):
      # autocompletamento
      self.timerForCmdAutoComplete.stop()

      # autocompletamento
      inputSearchOptions = QadVariables.get(QadMsg.translate("Environment variables", "INPUTSEARCHOPTIONS"))
      filterLen = len(filter)
      if filterLen < 2:
         return

      # inputSearcOptions & QadINPUTSEARCHOPTIONSEnum.ON = Turns on all automated keyboard features when typing at the Command prompt
      # inputSearcOptions & QadINPUTSEARCHOPTIONSEnum.AUTOCOMPLETE = Automatically appends suggestions as each keystroke is entered after the second keystroke.
      if inputSearchOptions & QadINPUTSEARCHOPTIONSEnum.ON and inputSearchOptions & QadINPUTSEARCHOPTIONSEnum.AUTOCOMPLETE:
         if filterLen >= 2:
            cmdName, qty = self.plugIn.getMoreUsedCmd(filter)
         else:
            cmdName = ""

         self.appendCmdTextForAutoComplete(cmdName, filterLen)


   def appendCmdTextForAutoComplete(self, cmdName, filterLen):
      cursor = self.textCursor()
      #cursor.movePosition(QTextCursor.End, QTextCursor.KeepAnchor)
      self.setTextCursor(cursor)
      if filterLen < len(cmdName): # if there is anything to add
         self.insertPlainText(cmdName[filterLen:])
      else:
         self.insertPlainText("")
      cursor.movePosition(QTextCursor.End, QTextCursor.MoveAnchor)
      cursor.movePosition(QTextCursor.Left, QTextCursor.KeepAnchor, len(cmdName) - filterLen)
      self.setTextCursor(cursor)
      self.refreshWidth()


   def showNextCmd(self):
      # shows the next command in the list of used commands
      cmdsHistory = self.plugIn.cmdsHistory
      cmdsHistoryLen = len(cmdsHistory)
      if self.historyIndex < cmdsHistoryLen and cmdsHistoryLen > 0:
         self.historyIndex += 1
         if self.historyIndex < cmdsHistoryLen:
            self.showMsg(cmdsHistory[self.historyIndex])


   def showPreviousCmd(self):
      # shows the previous command in the list of used commands
      cmdsHistory = self.plugIn.cmdsHistory
      cmdsHistoryLen = len(cmdsHistory)
      if self.historyIndex > 0 and cmdsHistoryLen > 0:
         self.historyIndex -= 1
         if self.historyIndex < cmdsHistoryLen:
            self.showMsg(cmdsHistory[self.historyIndex])


   def showLastCmd(self):
      # shows and returns the last command in the list of used commands
      cmdsHistory = self.plugIn.cmdsHistory
      cmdsHistoryLen = len(cmdsHistory)
      if cmdsHistoryLen > 0:
         self.showMsg(cmdsHistory[cmdsHistoryLen - 1])
         return cmdsHistory[cmdsHistoryLen - 1]
      else:
         return ""


   # ============================================================================
   # keyPressEvent
   # ============================================================================
   def keyPressEvent(self, e):

      if self.plugIn.shortCutManagement(e): # if a shortcut key sequence has been handled
         return

      # if Up or Down is pressed
      if self.isVisibleCmdSuggestWindow() and \
         (e.key() == Qt.Key_Down or e.key() == Qt.Key_Up or e.key() == Qt.Key_PageDown or e.key() == Qt.Key_PageUp or
          e.key() == Qt.Key_End or e.key() == Qt.Key_Home):
         self.cmdSuggestWindow.keyPressEvent(e)
         return
      else:  # I hide the suggestion window
         self.lockedPos = False
         self.showCmdSuggestWindow(False)

      if e.key() == Qt.Key_Escape:
         cmdsHistory = self.plugIn.cmdsHistory
         self.historyIndex = len(cmdsHistory)
         self.QadDynamicInputObj.abort()
         return

      # if Return or Space is pressed, then perform the commands
      if e.key() == Qt.Key_Return or e.key() == Qt.Key_Space or e.key == Qt.Key_Enter:
         self.entered()
         return
      # if Up or Down is pressed
      elif e.key() == Qt.Key_Down:
         self.showNextCmd()
         return # to prevent the suggestion window from appearing
      elif e.key() == Qt.Key_Up:
         self.showPreviousCmd()
         return # to prevent the suggestion window from appearing
      else:
         if (e.key() != Qt.Key_Tab and e.key() != Qt.Key_Backtab) or \
            e.text() != "":
            # all other keystrokes get sent to the input line
            QTextEdit.keyPressEvent(self, e)
            self.refreshWidth()

      # I read the delay time in msec
      inputSearchDelay = QadVariables.get(QadMsg.translate("Environment variables", "INPUTSEARCHDELAY"))

      # suggestion list of similar commands
      currMsg = self.toPlainText()
      shot1 = lambda: self.showCmdSuggestWindow(True, currMsg)

      del self.timerForCmdSuggestWindow
      self.timerForCmdSuggestWindow = QTimer()
      self.timerForCmdSuggestWindow.setSingleShot(True)
      self.timerForCmdSuggestWindow.timeout.connect(shot1)
      self.timerForCmdSuggestWindow.start(inputSearchDelay)

      if e.text().isalnum(): # autocomplete if an alphanumeric key has been pressed
         shot2 = lambda: self.showCmdAutoComplete(self.toPlainText())
         del self.timerForCmdAutoComplete
         self.timerForCmdAutoComplete = QTimer()
         self.timerForCmdAutoComplete.setSingleShot(True)

         self.timerForCmdAutoComplete.timeout.connect(shot2)
         self.timerForCmdAutoComplete.start(inputSearchDelay)


   def entered(self):
      if self.QadDynamicInputObj.refreshResult() == True: # I recalculate the result
         self.QadDynamicInputObj.showEvaluateMsg(self.QadDynamicInputObj.resStr) # I use the result in string format
      self.reset()
      cmdsHistory = self.plugIn.cmdsHistory
      self.historyIndex = len(cmdsHistory)


   def isVisibleCmdSuggestWindow(self):
      if self.cmdSuggestWindow is None:
         return False
      return self.cmdSuggestWindow.isVisible()


# ===============================================================================
# QadDynamicInputPromptEdit
# ===============================================================================
class QadDynamicInputPromptEdit(QadDynamicEdit):
#    """
#    Class that handles dynamic message prompt input and choice of command options
#    """

   def __init__(self, QadDynamicInputObj):
      QadDynamicEdit.__init__(self, QadDynamicInputObj)

      foregroundColor = QColor(QadVariables.get(QadMsg.translate("Environment variables", "DYNEDITFORECOLOR")))
      backGroundColor = QColor(QadVariables.get(QadMsg.translate("Environment variables", "DYNEDITBACKCOLOR")))
      borderColor = QColor(QadVariables.get(QadMsg.translate("Environment variables", "DYNEDITBORDERCOLOR")))
      opacity = 100 - QadVariables.get(QadMsg.translate("Environment variables", "TOOLTIPTRANSPARENCY"))
      self.setColors(foregroundColor, backGroundColor, borderColor, backGroundColor, foregroundColor, opacity)
      self.show(False)


   def show(self, mode):
      if mode == False:
         QTextEdit.setVisible(self, False)
      else:
         QTextEdit.setVisible(self, True)


#    # ============================================================================
#    # keyPressEvent
#    # ============================================================================
#    def keyPressEvent(self, e):
#       pass


# ===============================================================================
# QadDynamicInputEdit
# ===============================================================================
class QadDynamicInputEdit(QadDynamicEdit):
#    """
#    Class that handles the dynamic input of a value
#    """

   def __init__(self, QadDynamicInputObj):
      QadDynamicEdit.__init__(self, QadDynamicInputObj)
      self.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)

      # the default is a non-zero real number
      self.inputMode = QadInputModeEnum.NOT_NULL
      self.inputType = QadInputTypeEnum.FLOAT

      self.lockable = True # indicates whether the edit value can be locked
      self.__lockedValue = False # indicates whether the value contained in the edit is locked

      foregroundColor = QColor(QadVariables.get(QadMsg.translate("Environment variables", "DYNEDITFORECOLOR")))
      backGroundColor = QColor(QadVariables.get(QadMsg.translate("Environment variables", "DYNEDITBACKCOLOR")))
      borderColor = QColor(QadVariables.get(QadMsg.translate("Environment variables", "DYNEDITBORDERCOLOR")))
      opacity = 100 - QadVariables.get(QadMsg.translate("Environment variables", "TOOLTIPTRANSPARENCY"))
      self.setColors(foregroundColor, backGroundColor, borderColor, backGroundColor, foregroundColor, opacity)

      # icona di lock
      fm = QFontMetrics(self.currentFont())
      height = self.height() - 4
      self.LockedIcon = QLabel(self)
      self.LockedIcon.resize(height, height)
      self.LockedIcon.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
      self.LockedIcon.setStyleSheet("border:0px;"); # without border
      pixmap = QPixmap(":/plugins/qad/icons/locked.svg").scaled(height, height)
      self.LockedIcon.setPixmap(pixmap)

      self.lineMarkerColor = QColor(QadVariables.get(QadMsg.translate("Environment variables", "DYNTRECKINGVECTORCOLOR")))
      self.lineMarkers = [] # list of RubberBands displayed

      self.show(False)


   # ============================================================================
   # __del__
   # ============================================================================
   def __del__(self):
      self.removeItems()


   def setLockedValue(self, mode):
      # True returns and the operation was successful
      if self.lockable == False: return False
      if self.__lockedValue != mode:
         self.__lockedValue = mode
         self.LockedIcon.setVisible(self.__lockedValue)
      self.refreshWidth()


   def isLockedValue(self):
      return self.__lockedValue


   # ============================================================================
   # removeItems
   # ============================================================================
   def removeItems(self):
      # I empty the line of markers by removing them from the canvas
      for lineMarker in self.lineMarkers:
         lineMarker.hide()
         self.plugIn.canvas.scene().removeItem(lineMarker)
      del self.lineMarkers[:]


   # ============================================================================
   # reset
   # ============================================================================
   def reset(self):
      QadDynamicEdit.reset(self)
      self.inputMode = QadInputModeEnum.NONE
      self.__lockedValue = False
      self.removeItems()


   # ============================================================================
   # show
   # ============================================================================
   def show(self, mode):
      QTextEdit.setVisible(self, mode)
      for lineMarker in self.lineMarkers:
         lineMarker.setVisible(mode)
      if mode == False:
         self.LockedIcon.setVisible(False)
      else:
         if self.isLockedValue():
            self.LockedIcon.setVisible(True)
         else:
            self.LockedIcon.setVisible(False)


   # ============================================================================
   # refreshWidth
   # ============================================================================
   def refreshWidth(self, updateCtrlsPos = True):
      height = self.height()
      fm = QFontMetrics(self.currentFont())
      boundingRect = fm.boundingRect(self.toPlainText())
      width = int(boundingRect.width() * 1.2) + 5

      dimLockedIcon = self.LockedIcon.height()
      offset = 2
      if self.isLockedValue():
         width = width + dimLockedIcon + offset # for lock icon
      else:
         width = width + offset # for lock icon

      canvasRect = self.canvas.rect()
      if width > canvasRect.width():
         width = canvasRect.width()

      self.resize(width, height)
      self.LockedIcon.move(width - dimLockedIcon - offset, height - dimLockedIcon - 2)
      if updateCtrlsPos: self.QadDynamicInputObj.moveCtrls()


   # ============================================================================
   # keyPressEvent
   # ============================================================================
   def keyPressEvent(self, e):
      if self.plugIn.shortCutManagement(e): # if a shortcut key sequence has been handled
         return

      if e.key() == Qt.Key_Tab:
         if self.checkValid() is not None:
            # move to the next edit
            self.QadDynamicInputObj.setNextCurrentEdit()
         else: # incorrect value
            pass

      elif e.key() == Qt.Key_Backtab:
         if self.checkValid() is not None:
            self.QadDynamicInputObj.setPrevCurrentEdit()
         else: # incorrect value
            pass

      elif e.key() == Qt.Key_Return or e.key == Qt.Key_Enter:
         self.QadDynamicInputObj.keyPressEvent(e) # I have it handled by QadDynamicInputObj
#          if self.isLockedValue() == True:
#             value = self.toPlainText()
#             snapType = str2snapTypeEnum(value)
#             if snapType != -1: # if a snap was forced
#                self.QadDynamicInputObj.keyPressEvent(e) # I let QadDynamicInputObj handle it
#             elif self.checkValid() is not None:
#                self.QadDynamicInputObj.keyPressEvent(e) # I let QadDynamicInputObj handle it
#          else:
#             self.QadDynamicInputObj.keyPressEvent(e) # I let QadDynamicInputObj handle it

      elif (e.key() == Qt.Key_Down or e.key() == Qt.Key_Up or e.key() == Qt.Key_PageDown or e.key() == Qt.Key_PageUp or \
            e.key() == Qt.Key_End or e.key() == Qt.Key_Home):
         pass # at the moment it has been decided not to show the options menu of the active command from here

      elif e.key() == Qt.Key_Comma: # ","
         self.QadDynamicInputObj.keyPressEvent(e) # I have it handled by QadDynamicInputObj

      # if it is not a string and it is a special character
      elif not (self.inputType & QadInputTypeEnum.STRING) and \
           (e.text() == "@" or e.text() == "#" or e.text() == "<"):
            self.QadDynamicInputObj.keyPressEvent(e) # I have it handled by QadDynamicInputObj

      elif e.key() == Qt.Key_Escape:
         self.QadDynamicInputObj.abort()

      else:
         previousTxt = self.toPlainText()
         QTextEdit.keyPressEvent(self, e)
         if self.lockable: # if it is possible to change the lock state
            currentTxt = self.toPlainText()
            if currentTxt == "":
               self.setLockedValue(False)
            elif currentTxt != previousTxt:
               self.setLockedValue(True)
         else:
            self.refreshWidth()


   # ============================================================================
   # focusInEvent
   # ============================================================================
   def focusInEvent(self, e):
      # change the color
      foregroundColor = QColor(Qt.GlobalColor.black)
      backGroundColor = QColor(Qt.GlobalColor.white)
      borderColor = QColor(QadVariables.get(QadMsg.translate("Environment variables", "DYNEDITBORDERCOLOR")))
      opacity = 100 - QadVariables.get(QadMsg.translate("Environment variables", "TOOLTIPTRANSPARENCY"))
      selectionColor = QColor(Qt.GlobalColor.white)
      selectionBackGroundColor = QColor(51, 153, 255) # azzurro (R=51 G=153 B=255)
      self.setColors(foregroundColor, backGroundColor, borderColor, selectionColor, selectionBackGroundColor, opacity)
      self.selectAllText() # I select all the text


   # ============================================================================
   # focusOutEvent
   # ============================================================================
   def focusOutEvent(self, e):
      # change the color
      foregroundColor = QColor(QadVariables.get(QadMsg.translate("Environment variables", "DYNEDITFORECOLOR")))
      backGroundColor = QColor(QadVariables.get(QadMsg.translate("Environment variables", "DYNEDITBACKCOLOR")))
      borderColor = QColor(QadVariables.get(QadMsg.translate("Environment variables", "DYNEDITBORDERCOLOR")))
      opacity = 100 - QadVariables.get(QadMsg.translate("Environment variables", "TOOLTIPTRANSPARENCY"))
      self.setColors(foregroundColor, backGroundColor, borderColor, backGroundColor, foregroundColor, opacity)
      # I select the text
      cursor = self.textCursor()
      cursor.movePosition(QTextCursor.End, QTextCursor.MoveAnchor)
      cursor.movePosition(QTextCursor.End, QTextCursor.KeepAnchor)
      self.setTextCursor(cursor)


   # ============================================================================
   # checkValid
   # ============================================================================
   def checkValid(self):
      # returns None on error
      value = self.toPlainText()
      self.error = False

      if value == "" and (self.inputMode & QadInputModeEnum.NOT_NULL): # non permesso input nullo
         self.error = True
         self.setColors() # recolors with red borders because error=True
         self.selectAllText() # I select all the text
         return None

      if self.inputType & QadInputTypeEnum.INT or self.inputType & QadInputTypeEnum.LONG or \
         self.inputType & QadInputTypeEnum.FLOAT or self.inputType & QadInputTypeEnum.ANGLE:
         if self.inputType & QadInputTypeEnum.INT: # expects an integer
            value = qad_utils.str2int(value)
            if value is None:
               self.error = True
               self.setColors() # recolors with red borders because error=True
               self.selectAllText() # I select all the text
               return None
         elif self.inputType & QadInputTypeEnum.LONG: # expects a long number
            value = qad_utils.str2long(value)
            if value is None:
               self.error = True
               self.setColors() # recolors with red borders because error=True
               self.selectAllText() # I select all the text
               return None
         elif self.inputType & QadInputTypeEnum.FLOAT or self.inputType & QadInputTypeEnum.ANGLE: # expects a real number
            value = qad_utils.str2float(value)
            if value is None:
               self.error = True
               self.setColors() # recolors with red borders because error=True
               self.selectAllText() # I select all the text
               return None

         # not allowed value = 0
         # not allowed value < 0
         # not allowed value > 0
         if (value == 0 and (self.inputMode & QadInputModeEnum.NOT_ZERO)) or \
            (value < 0 and (self.inputMode & QadInputModeEnum.NOT_NEGATIVE)) or \
            (value > 0 and (self.inputMode & QadInputModeEnum.NOT_POSITIVE)):
            self.error = True
            self.setColors() # recolors with red borders because error=True
            self.selectAllText() # I select all the text
            return None

         if self.inputType & QadInputTypeEnum.ANGLE: # expects an angle in degrees
            if value is not None:
               # i gradi vanno convertiti in radianti
               value = float(qad_utils.toRadians(value))

      elif self.inputType & QadInputTypeEnum.BOOL:
         value = qad_utils.str2bool(value)
         if value is None:
            self.error = True
            self.setColors() # recolors with red borders because error=True
            self.selectAllText() # I select all the text
            return None

      return value


   # ============================================================================
   # setLinesMarker
   # ============================================================================
   def setLinesMarker(self, points):
      """Create a linear marker x a list of points"""
      # I empty the line of markers by removing them from the canvas
      for lineMarker in self.lineMarkers:
         lineMarker.hide()
         self.plugIn.canvas.scene().removeItem(lineMarker)
      del self.lineMarkers[:]

      lineMarker = createRubberBand(self.canvas, QgsWkbTypes.LineGeometry, True)
      lineMarker.setColor(self.lineMarkerColor)
      lineMarker.setLineStyle(Qt.DotLine)
      if points is None:
         return None
      tot = len(points)
      i = 0
      while i < (tot - 1):
         lineMarker.addPoint(points[i], False)
         i = i + 1
      lineMarker.addPoint(points[i], True)
      self.lineMarkers.append(lineMarker)



# ===============================================================================
class QadDynamicInput(QWidget):
# ===============================================================================
#    """
#    Base class that handles dynamic input
#    """


   # ============================================================================
   # __init__
   # ============================================================================
   def __init__(self, plugIn):
      QWidget.__init__(self, plugIn.canvas)
      self.plugIn = plugIn
      self.canvas = self.plugIn.canvas
      self.prevPart = None # part preceding the point to be moved in grip mode
      self.nextPart = None # next part the point to be moved in grip mode

      self.resValue = None    # resulting value
      self.resStr = ""        # risultato in formato stringa

      self.default = None
      self.mousePos = QPoint()
      self.isVisible = False

      self.initGui()
      self.currentEdit = None
      self.refreshOnEnvVariables()


   # ============================================================================
   # __del__
   # ============================================================================
   def __del__(self):
      self.removeItems()


   # ============================================================================
   # getPrompt
   # ============================================================================
   def getPrompt(self):
       return self.edits[QadDynamicInputEditEnum.PROMPT_EDIT].toPlainText()


   # ============================================================================
   # setPrevPart
   # ============================================================================
   def setPrevPart(self, linearObject):
      if linearObject is None:
         if self.prevPart is not None:
            del self.prevPart
            self.prevPart = None
      else:
         if self.prevPart is None:
            self.prevPart = linearObject.copy()
         else:
            self.prevPart.set(linearObject)


   # ============================================================================
   # setNextPart
   # ============================================================================
   def setNextPart(self, linearObject):
      if linearObject is None:
         if self.nextPart is not None:
            del self.nextPart
            self.nextPart = None
      else:
         if self.nextPart is None:
            self.nextPart = linearObject.copy()
         else:
            self.nextPart.set(linearObject)


   # ============================================================================
   # removeItems
   # ============================================================================
   def removeItems(self):
      self.show(False)
      for edit in self.edits:
         edit.removeItems()

      self.setPrevPart(None)
      self.setNextPart(None)


   # ============================================================================
   # refreshOnEnvVariables
   # ============================================================================
   def refreshOnEnvVariables(self):
      # DYNDIGRIP = Controls the display of dynamic dimensions when editing grip stretch
      self.dynDiGrip = QadVariables.get(QadMsg.translate("Environment variables", "DYNDIGRIP"))
      # DYNDIVIS = Controls the number of dynamic dimensions displayed when editing grip stretch
      self.dynDiVis = QadVariables.get(QadMsg.translate("Environment variables", "DYNDIVIS"))
      # DYNMODE = Enables and disables dynamic input functions
      self.dynMode = QadVariables.get(QadMsg.translate("Environment variables", "DYNMODE"))
      # DYNPICOORDS = Determines whether pointer input uses a relative or absolute format for coordinates
      self.dynPiCoords = QadVariables.get(QadMsg.translate("Environment variables", "DYNPICOORDS"))
      # DYNPIFORMAT = Determines whether the pointer input uses a polar or Cartesian format for coordinates
      self.dynPiFormat = QadVariables.get(QadMsg.translate("Environment variables", "DYNPIFORMAT"))
      # DYNPIVIS = Controls when pointer input is displayed
      self.dynPiVis = QadVariables.get(QadMsg.translate("Environment variables", "DYNPIVIS"))
      # DYNPROMPT = Controls the display of prompts in dynamic input descriptions
      self.dynPrompt = QadVariables.get(QadMsg.translate("Environment variables", "DYNPROMPT"))


   # ============================================================================
   # setColors
   # ============================================================================
   def setColors(self):
      opacity = 100 - QadVariables.get(QadMsg.translate("Environment variables", "TOOLTIPTRANSPARENCY"))
      foregroundColor = QColor(QadVariables.get(QadMsg.translate("Environment variables", "DYNEDITFORECOLOR")))
      backGroundColor = QColor(QadVariables.get(QadMsg.translate("Environment variables", "DYNEDITBACKCOLOR")))
      borderColor = QColor(QadVariables.get(QadMsg.translate("Environment variables", "DYNEDITBORDERCOLOR")))

      for i in range(0, len(self.edits), 1):
         if i == QadDynamicInputEditEnum.CMD_LINE_EDIT: # for CMD_LINE_EDIT
            cmdForegroundColor = QColor(QadVariables.get(QadMsg.translate("Environment variables", "CMDLINEFORECOLOR")))
            cmdBackGroundColor = QColor(QadVariables.get(QadMsg.translate("Environment variables", "CMDLINEBACKCOLOR")))
            self.edits[QadDynamicInputEditEnum.CMD_LINE_EDIT].setColors(cmdForegroundColor, cmdBackGroundColor, None, \
                                                                        cmdBackGroundColor, cmdForegroundColor, opacity)
         else: # all edits except CMD_LINE_EDIT
            self.edits[i].setColors(foregroundColor, backGroundColor, borderColor, backGroundColor, foregroundColor, opacity)


   def isActive(self):
      # returns True if dynamic input is enabled
      return True if self.dynMode > 0 else False


   def isPointInputOn(self): # returns True if pointer input enabled
      return True if self.dynMode & 1 else False


   def isDimensionalInputOn(self): # returns True if dimension input activated
      return True if self.dynMode & 2 else False


   def isPromptActive(self):
      return True if self.isActive() and self.dynPrompt == 1 else False


   def hasFocus(self): # returns True if an input widget has focus
      for edit in self.edits:
         if edit.hasFocus(): return True
      return False


   # ============================================================================
   # initGui
   # ============================================================================
   def initGui(self):
      # create an array of edits
      self.edits = [None] * 15 # see QadDynamicInputEditEnum for the number of elements

      # used to enter a command
      self.edits[QadDynamicInputEditEnum.CMD_LINE_EDIT] = QadDynamicInputCmdLineEdit(self)
      # used for messages and command option selection
      self.edits[QadDynamicInputEditEnum.PROMPT_EDIT] = QadDynamicInputPromptEdit(self)

      # used for generic request (e.g. radius, scale, angle)
      self.edits[QadDynamicInputEditEnum.EDIT] = QadDynamicInputEdit(self)
      self.edits[QadDynamicInputEditEnum.EDIT].lockable == False # non-lockable value

      # used to indicate whether absolute coordinate "#" or relative "@" and whether Cartesian or polar "<"
      self.edits[QadDynamicInputEditEnum.EDIT_SYMBOL_COORD_TYPE] = QadDynamicInputEdit(self)
      self.edits[QadDynamicInputEditEnum.EDIT_SYMBOL_COORD_TYPE].inputMode = QadInputModeEnum.NONE
      self.edits[QadDynamicInputEditEnum.EDIT_SYMBOL_COORD_TYPE].inputType = QadInputTypeEnum.STRING
      # used for X coordinate
      self.edits[QadDynamicInputEditEnum.EDIT_X] = QadDynamicInputEdit(self)
      self.edits[QadDynamicInputEditEnum.EDIT_X].inputMode = QadInputModeEnum.NOT_NULL
      self.edits[QadDynamicInputEditEnum.EDIT_X].inputType = QadInputTypeEnum.FLOAT
      # used for Y coordinate
      self.edits[QadDynamicInputEditEnum.EDIT_Y] = QadDynamicInputEdit(self)
      self.edits[QadDynamicInputEditEnum.EDIT_Y].inputMode = QadInputModeEnum.NOT_NULL
      self.edits[QadDynamicInputEditEnum.EDIT_Y].inputType = QadInputTypeEnum.FLOAT
      # used for Z coordinate
      self.edits[QadDynamicInputEditEnum.EDIT_Z] = QadDynamicInputEdit(self)
      self.edits[QadDynamicInputEditEnum.EDIT_Z].inputMode = QadInputModeEnum.NOT_NULL
      self.edits[QadDynamicInputEditEnum.EDIT_Z].inputType = QadInputTypeEnum.FLOAT

      # used for distance from previous point
      self.edits[QadDynamicInputEditEnum.EDIT_DIST_PREV_PT] = QadDynamicInputEdit(self)
      self.edits[QadDynamicInputEditEnum.EDIT_DIST_PREV_PT].inputMode = QadInputModeEnum.NOT_NULL
      self.edits[QadDynamicInputEditEnum.EDIT_DIST_PREV_PT].inputType = QadInputTypeEnum.FLOAT

      # used for distance more or less than the distance from the previous point
      self.edits[QadDynamicInputEditEnum.EDIT_REL_DIST_PREV_PT] = QadDynamicInputEdit(self)
      self.edits[QadDynamicInputEditEnum.EDIT_REL_DIST_PREV_PT].inputMode = QadInputModeEnum.NOT_NULL
      self.edits[QadDynamicInputEditEnum.EDIT_REL_DIST_PREV_PT].inputType = QadInputTypeEnum.FLOAT

      # used for corner from previous point
      self.edits[QadDynamicInputEditEnum.EDIT_ANG_PREV_PT] = QadDynamicInputEdit(self)
      self.edits[QadDynamicInputEditEnum.EDIT_ANG_PREV_PT].inputMode = QadInputModeEnum.NOT_NULL
      self.edits[QadDynamicInputEditEnum.EDIT_ANG_PREV_PT].inputType = QadInputTypeEnum.ANGLE

      # used for angle more or less than the angle from the previous point
      self.edits[QadDynamicInputEditEnum.EDIT_REL_ANG_PREV_PT] = QadDynamicInputEdit(self)
      self.edits[QadDynamicInputEditEnum.EDIT_REL_ANG_PREV_PT].inputMode = QadInputModeEnum.NOT_NULL
      self.edits[QadDynamicInputEditEnum.EDIT_REL_ANG_PREV_PT].inputType = QadInputTypeEnum.ANGLE

      # used for distance to next point
      self.edits[QadDynamicInputEditEnum.EDIT_DIST_NEXT_PT] = QadDynamicInputEdit(self)
      self.edits[QadDynamicInputEditEnum.EDIT_DIST_NEXT_PT].inputMode = QadInputModeEnum.NOT_NULL
      self.edits[QadDynamicInputEditEnum.EDIT_DIST_NEXT_PT].inputType = QadInputTypeEnum.FLOAT

      # used for distance more or less than the distance to the next point
      self.edits[QadDynamicInputEditEnum.EDIT_REL_DIST_NEXT_PT] = QadDynamicInputEdit(self)
      self.edits[QadDynamicInputEditEnum.EDIT_REL_DIST_NEXT_PT].inputMode = QadInputModeEnum.NOT_NULL
      self.edits[QadDynamicInputEditEnum.EDIT_REL_DIST_NEXT_PT].inputType = QadInputTypeEnum.FLOAT

      # used for corner from next point
      self.edits[QadDynamicInputEditEnum.EDIT_ANG_NEXT_PT] = QadDynamicInputEdit(self)
      self.edits[QadDynamicInputEditEnum.EDIT_ANG_NEXT_PT].inputMode = QadInputModeEnum.NOT_NULL
      self.edits[QadDynamicInputEditEnum.EDIT_ANG_NEXT_PT].inputType = QadInputTypeEnum.ANGLE

      # used for angle more or less than the angle from the next point
      self.edits[QadDynamicInputEditEnum.EDIT_REL_ANG_NEXT_PT] = QadDynamicInputEdit(self)
      self.edits[QadDynamicInputEditEnum.EDIT_REL_ANG_NEXT_PT].inputMode = QadInputModeEnum.NOT_NULL
      self.edits[QadDynamicInputEditEnum.EDIT_REL_ANG_NEXT_PT].inputType = QadInputTypeEnum.ANGLE


   # ============================================================================
   # reset
   # ============================================================================
   def reset(self, default = None):
      return # da virtualizzare


   # ============================================================================
   # getInitialNdxEdit
   # ============================================================================
   # returns the position of the initial control
   def getInitialNdxEdit(self):
      return # da virtualizzare


   # ============================================================================
   # setInitialFocus
   # ============================================================================
   def setInitialFocus(self):
      for edit in self.edits:
         edit.setReadOnly(True)

      self.currentEdit = self.getInitialNdxEdit()

      if self.currentEdit is not None:
         widget = self.edits[self.currentEdit]
         widget.setReadOnly(False)
         #widget.setWindowFlags(widget.windowFlags() | Qt.WindowStaysOnTopHint)
         if widget.hasFocus(): # if it already has fire, I color the box and that's it
            widget.focusInEvent(None)
         else:
            widget.setFocus()
      else:
         self.canvas.setFocus()


   # ============================================================================
   # setFocus
   # ============================================================================
   def setFocus(self):
      if self.currentEdit is None: # if it is not set which edit is the current one
         self.setInitialFocus()
         return

      for edit in self.edits:
         edit.setReadOnly(True)

      self.edits[self.currentEdit].setReadOnly(False)
      self.edits[self.currentEdit].setFocus()


   # ============================================================================
   # getNextNdxEditSequence
   # ============================================================================
   # returns the position of the next control using the sequence
   def getNextNdxEditSequence(self, currentEdit):
      return # da virtualizzare


   # ============================================================================
   # setNextCurrentEdit
   # ============================================================================
   def setNextCurrentEdit(self):
      return # da virtualizzare


   # ============================================================================
   # getPrevNdxEditSequence
   # ============================================================================
   # returns the position of the previous control using the sequence
   def getPrevNdxEditSequence(self, currentEdit):
      return # da virtualizzare


   # ============================================================================
   # setPrevCurrentEdit
   # ============================================================================
   def setPrevCurrentEdit(self):
      return # da virtualizzare


   # ============================================================================
   # isCoordWidgetVisib
   # ============================================================================
   def isCoordWidgetVisib(self):
      # returns whether coordinate widgets should be shown
      return # da virtualizzare


   # ============================================================================
   # isDimensionalWidgetVisib
   # ============================================================================
   def isDimensionalWidgetVisib(self):
      return # da virtualizzare


   # ============================================================================
   # anyLockedValueEdit
   # ============================================================================
   def anyLockedValueEdit(self):
      if self.edits[QadDynamicInputEditEnum.EDIT_X].isLockedValue(): return True
      if self.edits[QadDynamicInputEditEnum.EDIT_Y].isLockedValue(): return True
      if self.edits[QadDynamicInputEditEnum.EDIT_Z].isLockedValue(): return True
      if self.edits[QadDynamicInputEditEnum.EDIT].isLockedValue(): return True
      if self.edits[QadDynamicInputEditEnum.EDIT_DIST_PREV_PT].isLockedValue(): return True
      if self.edits[QadDynamicInputEditEnum.EDIT_REL_DIST_PREV_PT].isLockedValue(): return True
      if self.edits[QadDynamicInputEditEnum.EDIT_ANG_PREV_PT].isLockedValue(): return True
      if self.edits[QadDynamicInputEditEnum.EDIT_REL_ANG_PREV_PT].isLockedValue(): return True
      if self.edits[QadDynamicInputEditEnum.EDIT_DIST_NEXT_PT].isLockedValue(): return True
      if self.edits[QadDynamicInputEditEnum.EDIT_REL_DIST_NEXT_PT].isLockedValue(): return True
      if self.edits[QadDynamicInputEditEnum.EDIT_ANG_NEXT_PT].isLockedValue(): return True
      if self.edits[QadDynamicInputEditEnum.EDIT_REL_ANG_NEXT_PT].isLockedValue(): return True
      return False


   # ============================================================================
   # setDefault
   # ============================================================================
   def setDefault(self, default):
      # da virtualizzare
      return


   # ============================================================================
   # show
   # ============================================================================
   def show(self, mode, mousePos = None, prompt = None, default = None):
      # da virtualizzare
      return


   # ============================================================================
   # showErr
   # ============================================================================
   def showErr(self, err = ""):
      # da virtualizzare
      return


   # ============================================================================
   # showInputMsg
   # ============================================================================
   def showInputMsg(self, inputMsg = None, inputType = QadInputTypeEnum.COMMAND, \
                    default = None, keyWords = "", inputMode = QadInputModeEnum.NONE):
      # da virtualizzare
      return


   # ============================================================================
   # mouseMoveEvent
   # ============================================================================
   def mouseMoveEvent(self, mousePos):
      # da virtualizzare
      return


   # ============================================================================
   # moveCtrls
   # ============================================================================
   def moveCtrls(self, mousePos = None):
      # move all visible widgets depending on the context
      # da virtualizzare
      return


   # ============================================================================
   # getPosAndLineMarkerForLine
   # ============================================================================
   def getPosAndLineMarkerForLine(self, pt1, pt2, offset, editWidget):
      # Returns the position of an edit widget that will be placed at the midpoint of a line
      # having pt1 as the starting point, pt2 as the ending point but shifted by an offset.
      # The function also returns the lines to use as marker lines
      # coordinates must be expressed in map coordinates
      angle = qad_utils.getAngleBy2Pts(pt1, pt2, 0) # without tolerance
      if angle >= 0 and angle < math.pi:
         angle = angle + math.pi / 2
      else:
         angle = angle - math.pi / 2

      pt = qad_utils.getMiddlePoint(pt1, pt2)

      editPt = qad_utils.getPolarPointByPtAngle(pt, angle, offset)
      editPt = self.canvas.getCoordinateTransform().transform(editPt) # Transform the point from map (world) coordinates to device coordinates

      editWidth = editWidget.width()
      editHeight = editWidget.height()
      x = editPt.x() - (editWidth / 2)
      y = editPt.y() - (editHeight / 2)

      x, y = self.adjustEditPosition(x, y, editWidth, editHeight)
      editPt = QPoint(x, y);

      pt1Corner = qad_utils.getPolarPointByPtAngle(pt1, angle, offset)
      pt2Corner = qad_utils.getPolarPointByPtAngle(pt2, angle, offset)

      return editPt, [pt1, pt1Corner, pt2Corner, pt2]


   # ============================================================================
   # getPosAndLineMarkerForArc
   # ============================================================================
   def getPosAndLineMarkerForArc(self, start, center, end, offset, editWidget, LineMarkerOnlyArc = False):
      # Returns the position of an edit widget that will be placed at the midpoint of an arc
      # having start, the initial point, center as the center and end as the final point
      # The function also returns the lines that form the arc to use as marker lines
      # if LineMarkerOnlyArc = True then only the arc will be returned otherwise
      # a line will be added starting from the center of the arc
      arc1 = QadArc()
      if arc1.fromStartCenterEndPts(start, center, end) == False:
         return self.getPosAndLineMarkerForLine(center, end, offset, editWidget)

      arc2 = QadArc()
      if arc2.fromStartCenterEndPts(end, center, start) == False:
         return self.getPosAndLineMarkerForLine(center, end, offset, editWidget)

      if arc1.length() <= arc2.length():
         arc1.radius = arc1.radius + offset
         pos, lineMarker = self.getPosAndLineMarkerForArcObj(arc1, editWidget)
         if LineMarkerOnlyArc == False and lineMarker is not None:
            lineMarker.insert(0, center)
      else:
         arc2.radius = arc2.radius + offset
         pos, lineMarker = self.getPosAndLineMarkerForArcObj(arc2, editWidget)
         if LineMarkerOnlyArc == False and lineMarker is not None:
            lineMarker.append(center)

      return pos, lineMarker


   # ============================================================================
   # getPosAndLineMarkerForArcObj
   # ============================================================================
   def getPosAndLineMarkerForArcObj(self, arc, editWidget):
      # Returns the position of an edit widget that will be placed at the midpoint of an arc
      # The function also returns the lines that form the arc to use as marker lines
      editPt = arc.getMiddlePt()
      editPt = self.canvas.getCoordinateTransform().transform(editPt) # Transform the point from map (world) coordinates to device coordinates

      editWidth = editWidget.width()
      editHeight = editWidget.height()
      x = editPt.x() - (editWidth / 2)
      y = editPt.y() - (editHeight / 2)

      x, y = self.adjustEditPosition(x, y, editWidth, editHeight)
      editPt = QPoint(x, y)

      return editPt, arc.asPolyline()


   # ============================================================================
   # adjustEditPosition
   # ============================================================================
   def adjustEditPosition(self, x, y, width, height):
      # adjust the position of an edit widget so that it does not leave the canvas window
      canvasRect = self.plugIn.canvas.rect()
      offsetY = height

      if x < 0: x = 0
      else:
         overflow = x + width - canvasRect.width()
         if overflow > 0: x = x - overflow

      if y < 0: y = 0
      else:
         overflow = y + height + offsetY - canvasRect.height()
         if overflow > 0: y = y - overflow

      # to prevent the mouse from overlapping I move the widget above the mouse (I keep 5 pixels of offset around the widget)
      if self.mousePos is not None:
         if self.mousePos.x() >= x - 5 and self.mousePos.x() <= x + width + 5 and \
            self.mousePos.y() >= y - 5 and self.mousePos.y() <= y + height + 5:
            if canvasRect.bottom() - self.mousePos.y() < self.mousePos.y():
               y = self.mousePos.y() - height - offsetY
            else:
               y = self.mousePos.y() + offsetY

      return int(x), int(y)


   # ============================================================================
   # refreshResult
   # ============================================================================
   def refreshResult(self, mousePos = None):
      # calculates the result and returns True if the operation is successful
      # the result is also set in self.resValue and, in string format, in self.resStr
      # da virtualizzare
      return


   # ============================================================================
   # showEvaluateMsg
   # ============================================================================
   def showEvaluateMsg(self, msg):
      if self.isActive() == False or self.isVisible == False: return
      self.plugIn.showEvaluateMsg(msg)


   # ============================================================================
   # keyPressEvent
   # ============================================================================
   def keyPressEvent(self, e):
      # da virtualizzare
      return


   # ============================================================================
   # abort
   # ============================================================================
   def abort(self):
      self.isVisible = False
      for edit in self.edits:
         edit.show(False)

      self.show(False)
      self.plugIn.abortCommand()
      self.plugIn.clearCurrentObjsSelection()
      self.canvas.setFocus()



# ===============================================================================
class QadDynamicCmdInput(QadDynamicInput):
# ===============================================================================
#    """
#    Base class that handles dynamic input for new command input
#    """


   # ============================================================================
   # __init__
   # ============================================================================
   def __init__(self, plugIn):
      QadDynamicInput.__init__(self, plugIn)

      self.resValue = None    # resulting value
      self.resStr = ""        # risultato in formato stringa

      self.default = None
      self.mousePos = QPoint()
      self.isVisible = False

      self.initGui()
      self.currentEdit = None


   # ============================================================================
   # reset
   # ============================================================================
   def reset(self, default = None):
      # the function should not reset self.prevPart, self.nextPart
      self.currentEdit = None

      for i in range(0, len(self.edits), 1):
         self.edits[i].reset()

      # update all control colors
      self.setColors()
      # if there is a default value set it
      if default is not None:
         self.setDefault(default)

      # commented because it creates problems when you select an object and move the mouse to a grip point (deselects the object)
      #self.plugIn.clearCurrentObjsSelection()


   # ============================================================================
   # getInitialNdxEdit
   # ============================================================================
   # returns the position of the initial control
   def getInitialNdxEdit(self):
      return QadDynamicInputEditEnum.CMD_LINE_EDIT


   # ============================================================================
   # getNextNdxEditSequence
   # ============================================================================
   # returns the position of the next control using the sequence
   def getNextNdxEditSequence(self, currentEdit):
      return QadDynamicInputEditEnum.CMD_LINE_EDIT


   # ============================================================================
   # setNextCurrentEdit
   # ============================================================================
   def setNextCurrentEdit(self):
      if self.currentEdit is None: # if it is not set which edit is the current one
         self.setInitialFocus()
         return

      self.currentEdit = self.getNextNdxEditSequence(self.currentEdit)

      self.setFocus()


   # ============================================================================
   # getPrevNdxEditSequence
   # ============================================================================
   # returns the position of the previous control using the sequence
   def getPrevNdxEditSequence(self, currentEdit):
      return QadDynamicInputEditEnum.CMD_LINE_EDIT


   # ============================================================================
   # setPrevCurrentEdit
   # ============================================================================
   def setPrevCurrentEdit(self):
      if self.currentEdit is None: # if it is not set which edit is the current one
         self.setInitialFocus()
         return

      self.currentEdit = self.getNextNdxEditSequence(self.currentEdit)

      self.setFocus()


   # ============================================================================
   # isCoordWidgetVisib
   # ============================================================================
   def isCoordWidgetVisib(self):
      # returns whether coordinate widgets should be shown
      # if pointer input is enabled and coordinate display is set by dynPiVis = 2 (always display)
      if self.isPointInputOn() and self.dynPiVis == 2:
         return True
      else:
         return False


   # ============================================================================
   # isDimensionalWidgetVisib
   # ============================================================================
   def isDimensionalWidgetVisib(self):
      # if height input is not enabled
      if self.isDimensionalInputOn() == False: return False
      # whether there is a preceding part or a subsequent part
      if self.prevPart is not None or self.nextPart is not None:
         return True
      else:
         return False


   # ============================================================================
   # setDefault
   # ============================================================================
   def setDefault(self, default):
      self.default = default
      self.edits[QadDynamicInputEditEnum.CMD_LINE_EDIT].showMsg(self.default)


   # ============================================================================
   # setPrevNextPart
   # ============================================================================
   def setPrevNextPart(self, entity, gripPoint):
      # entity is of type QadEntity
      # gripPoint is of type QadEntityGripPoint
      prevPart = None
      nextPart = None
      # check if the entity belongs to a dimensioning style
      if QadDimStyles.isDimEntity(entity):
         pass
      else:
         qadGeom = entity.getQadGeom(gripPoint.atGeom, gripPoint.atSubGeom)
         qadGeomType = qadGeom.whatIs()
         if qadGeomType == "ARC" or qadGeomType == "ELLIPSE_ARC":
            if gripPoint.gripType == QadGripPointTypeEnum.ARC_MID_POINT:
               prevPart = qadGeom.copy()
               nextPart = qadGeom.copy()
            else:
               if qad_utils.ptNear(qadGeom.getStartPt(), gripPoint.getPoint()):
                  nextPart = qadGeom.copy()
               elif qad_utils.ptNear(qadGeom.getEndPt(), gripPoint.getPoint()):
                  prevPart = qadGeom.copy()

         elif qadGeomType == "POLYLINE":
            prevPart, nextPart = qadGeom.getPrevNextLinearObjectsAtVertex(gripPoint.nVertex)
            if (gripPoint.gripType == QadGripPointTypeEnum.LINE_MID_POINT or \
                gripPoint.gripType == QadGripPointTypeEnum.ARC_MID_POINT) and \
               nextPart is not None:
               prevPart = nextPart.copy()

         elif qadGeomType == "CIRCLE":
            if qadGeom.isPtOnCircle(gripPoint.getPoint()):
               prevPart = QadLine()
               prevPart.set(qadGeom.center, gripPoint.getPoint())

         elif qadGeomType == "ELLIPSE":
            if qadGeom.containsPt(gripPoint.getPoint()):
               prevPart = QadLine()
               prevPart.set(qadGeom.center, gripPoint.getPoint())

      self.setPrevPart(prevPart)
      self.setNextPart(nextPart)


   # ============================================================================
   # show
   # ============================================================================
   def show(self, mode, mousePos = None, prompt = None, default = None):
      # if it's about making invisible I do it regardless of whether it's active or not
      # (used to manage F12)
      if mode == False:
         self.isVisible = False
         for edit in self.edits:
            edit.show(False)
         return False

      if self.isActive() == False: return False

      # if the mouse position is passed the function
      # resets dynamic input state (errors, fire)
      if mousePos is not None:
         self.reset(default)

      if prompt is not None:
         self.edits[QadDynamicInputEditEnum.PROMPT_EDIT].showMsg(prompt, False, False, False) # without updating the position of the controls

      self.isVisible = True

      visibList = [False] * len(self.edits)

      if self.isPromptActive() and len(self.edits[QadDynamicInputEditEnum.PROMPT_EDIT].toPlainText()) > 0:
         visibList[QadDynamicInputEditEnum.PROMPT_EDIT] = True

      if len(self.edits[QadDynamicInputEditEnum.CMD_LINE_EDIT].toPlainText()) > 0:
         visibList[QadDynamicInputEditEnum.CMD_LINE_EDIT] = True
      else:
         # if I need to display coordinate widgets
         if self.isCoordWidgetVisib():
            visibList[QadDynamicInputEditEnum.EDIT_X] = True
            visibList[QadDynamicInputEditEnum.EDIT_Y] = True
         # if I need to show the odds widgets
         if self.isDimensionalWidgetVisib():
            if self.prevPart is not None:
               gType = self.prevPart.whatIs()
               if gType == "LINE":
                  visibList[QadDynamicInputEditEnum.EDIT_DIST_PREV_PT] = True # used for previous segment length
               elif gType == "ARC": # arc
                  visibList[QadDynamicInputEditEnum.EDIT_DIST_PREV_PT] = True # used for arc radius length
                  visibList[QadDynamicInputEditEnum.EDIT_REL_DIST_PREV_PT] = True # used for arc radius length
                  visibList[QadDynamicInputEditEnum.EDIT_ANG_PREV_PT] = True # used for arc corner at the end point of the previous part

            if self.nextPart is not None:
               gType = self.nextPart.whatIs()
               if gType == "LINE":
                  visibList[QadDynamicInputEditEnum.EDIT_DIST_NEXT_PT] = True # used for next segment length
               elif gType == "ARC": # arc
                  # if nextPart and prevPart are equal
                  if self.prevPart is not None and self.nextPart == self.prevPart:
                     visibList[QadDynamicInputEditEnum.EDIT_REL_ANG_PREV_PT] = True # used for total arc angle
                     visibList[QadDynamicInputEditEnum.EDIT_REL_DIST_PREV_PT] = False # used for arc radius length previous part
                  else:
                     visibList[QadDynamicInputEditEnum.EDIT_DIST_NEXT_PT] = True # used for arc radius length
                     visibList[QadDynamicInputEditEnum.EDIT_REL_DIST_NEXT_PT] = True # used for arc radius length
                  visibList[QadDynamicInputEditEnum.EDIT_ANG_NEXT_PT] = True # used for arc corner at the starting point of the next part

      for i in range(0, len(self.edits), 1):
         self.edits[i].show(visibList[i])

      self.setFocus()

      # riposiziono i widget
      if mousePos is None:
         self.mouseMoveEvent(self.canvas.mouseLastXY())
      else:
         self.mouseMoveEvent(mousePos)

      return self.isVisible


   # ============================================================================
   # showErr
   # ============================================================================
   def showErr(self, err = ""):
      if self.isActive() == False: return

      self.edits[QadDynamicInputEditEnum.CMD_LINE_EDIT].show(False)
      if self.isPromptActive():
         self.edits[QadDynamicInputEditEnum.PROMPT_EDIT].error = True
         self.edits[QadDynamicInputEditEnum.PROMPT_EDIT].setColors() # recolors with red borders because error=True
         self.edits[QadDynamicInputEditEnum.PROMPT_EDIT].show(True)
         self.edits[QadDynamicInputEditEnum.PROMPT_EDIT].showMsg(err)

         self.canvas.setFocus()

      self.moveCtrls() # to reposition the controls


   # ============================================================================
   # mouseMoveEvent
   # ============================================================================
   def mouseMoveEvent(self, mousePos):
      if self.isActive() == False or self.isVisible == False: return

      point = self.canvas.getCoordinateTransform().toMapCoordinates(mousePos) # posizione

      # if coordinate widgets are visible
      if self.edits[QadDynamicInputEditEnum.EDIT_X].isVisible():
         self.edits[QadDynamicInputEditEnum.EDIT_X].showMsg(qad_utils.numToStringFmt(point.x()), False, False, False) # without updating the position of the controls
         self.edits[QadDynamicInputEditEnum.EDIT_Y].showMsg(qad_utils.numToStringFmt(point.y()), False, False, False) # without updating the position of the controls

      if self.prevPart is not None:
         gType = self.prevPart.whatIs()
         if gType == "LINE":
            if self.edits[QadDynamicInputEditEnum.EDIT_DIST_PREV_PT].isVisible():
               # used for previous segment length
               self.edits[QadDynamicInputEditEnum.EDIT_DIST_PREV_PT].showMsg(qad_utils.numToStringFmt(self.prevPart.length()), False, False, False) # without updating the position of the controls
         elif gType == "ARC":
            if self.edits[QadDynamicInputEditEnum.EDIT_DIST_PREV_PT].isVisible():
               # used for arc radius length
               self.edits[QadDynamicInputEditEnum.EDIT_DIST_PREV_PT].showMsg(qad_utils.numToStringFmt(self.prevPart.radius), False, False, False) # without updating the position of the controls

            if self.edits[QadDynamicInputEditEnum.EDIT_REL_DIST_PREV_PT].isVisible():
               # used for arc radius length
               self.edits[QadDynamicInputEditEnum.EDIT_REL_DIST_PREV_PT].showMsg(qad_utils.numToStringFmt(self.prevPart.radius), False, False, False) # without updating the position of the controls

            if self.edits[QadDynamicInputEditEnum.EDIT_ANG_PREV_PT].isVisible():
               # used for arc corner at the end point of the previous part
               if self.prevPart.reversed:
                  angle = self.prevPart.startAngle
               else:
                  angle = self.prevPart.endAngle

               if angle >= math.pi and angle < 2 * math.pi:
                  angle = 2 * math.pi - angle
               msg = qad_utils.numToStringFmt(qad_utils.toDegrees(angle)) + u'\N{DEGREE SIGN}' # simbolo dei gradi
               self.edits[QadDynamicInputEditEnum.EDIT_ANG_PREV_PT].showMsg(msg, False, False, False) # without updating the position of the controls

      if self.nextPart is not None:
         gType = self.nextPart.whatIs()
         if gType == "LINE":
            if self.edits[QadDynamicInputEditEnum.EDIT_DIST_NEXT_PT].isVisible():
               # used for next segment length
               self.edits[QadDynamicInputEditEnum.EDIT_DIST_NEXT_PT].showMsg(qad_utils.numToStringFmt(self.nextPart.length()), False, False, False) # without updating the position of the controls
         elif gType == "ARC":
            if self.edits[QadDynamicInputEditEnum.EDIT_DIST_NEXT_PT].isVisible():
               # used for arc radius length
               self.edits[QadDynamicInputEditEnum.EDIT_DIST_NEXT_PT].showMsg(qad_utils.numToStringFmt(self.nextPart.radius), False, False, False) # without updating the position of the controls

            if self.edits[QadDynamicInputEditEnum.EDIT_REL_DIST_NEXT_PT].isVisible():
               # used for arc radius length
               self.edits[QadDynamicInputEditEnum.EDIT_REL_DIST_NEXT_PT].showMsg(qad_utils.numToStringFmt(self.nextPart.radius), False, False, False) # without updating the position of the controls

            if self.edits[QadDynamicInputEditEnum.EDIT_ANG_NEXT_PT].isVisible():
               # used for arc corner at the starting point of the next part
               if self.nextPart.reversed:
                  angle = self.nextPart.endAngle
               else:
                  angle = self.nextPart.startAngle

               if angle >= math.pi and angle < 2 * math.pi:
                  angle = 2 * math.pi - angle
               msg = qad_utils.numToStringFmt(qad_utils.toDegrees(angle)) + u'\N{DEGREE SIGN}' # simbolo dei gradi
               self.edits[QadDynamicInputEditEnum.EDIT_ANG_NEXT_PT].showMsg(msg, False, False, False) # without updating the position of the controls

            # if nextPart and prevPart are equal
            if self.edits[QadDynamicInputEditEnum.EDIT_REL_ANG_PREV_PT].isVisible():
               # used for total arc angle
               msg = qad_utils.numToStringFmt(qad_utils.toDegrees(self.nextPart.totalAngle())) + u'\N{DEGREE SIGN}' # simbolo dei gradi
               self.edits[QadDynamicInputEditEnum.EDIT_REL_ANG_PREV_PT].showMsg(msg, False, False, False) # without updating the position of the controls


      if self.currentEdit is not None:
         self.edits[self.currentEdit].focusInEvent(None) # I bring the focus back to the current control

      self.moveCtrls(mousePos)

      return


   # ============================================================================
   # moveCtrls
   # ============================================================================
   def moveCtrls(self, mousePos = None):
      # move all visible widgets depending on the context
      if mousePos is not None:
         self.mousePos.setX(mousePos.x())
         self.mousePos.setY(mousePos.y())

      height = self.edits[QadDynamicInputEditEnum.CMD_LINE_EDIT].height()
      offset = 5

      width = 0
      if self.edits[QadDynamicInputEditEnum.PROMPT_EDIT].isVisible():
         width += self.edits[QadDynamicInputEditEnum.PROMPT_EDIT].width()

      x = self.mousePos.x() + height
      y = self.mousePos.y() + height

      if self.edits[QadDynamicInputEditEnum.PROMPT_EDIT].lockedPos or \
         self.edits[QadDynamicInputEditEnum.CMD_LINE_EDIT].lockedPos:
         return;
      if self.edits[QadDynamicInputEditEnum.CMD_LINE_EDIT].isVisible():
         if width > 0 : width += offset
         offsetX_cmdLineEdit = width
         width += self.edits[QadDynamicInputEditEnum.CMD_LINE_EDIT].width()

      x, y = self.adjustEditPosition(x, y, width, height)

      if self.edits[QadDynamicInputEditEnum.CMD_LINE_EDIT].isVisible():
         self.edits[QadDynamicInputEditEnum.CMD_LINE_EDIT].move(x + offsetX_cmdLineEdit, y)

      if self.edits[QadDynamicInputEditEnum.EDIT_X].isVisible() or \
         self.edits[QadDynamicInputEditEnum.EDIT_Y].isVisible():

         if self.edits[QadDynamicInputEditEnum.EDIT_X].isVisible():
            if width > 0 : width += offset
            offsetX_editX = width
            width += self.edits[QadDynamicInputEditEnum.EDIT_X].width()
         if self.edits[QadDynamicInputEditEnum.EDIT_Y].isVisible():
            if width > 0 : width += offset
            offsetX_editY = width
            width += self.edits[QadDynamicInputEditEnum.EDIT_Y].width()

         x, y = self.adjustEditPosition(x, y, width, height)

         if self.edits[QadDynamicInputEditEnum.EDIT_X].isVisible(): self.edits[QadDynamicInputEditEnum.EDIT_X].move(x + offsetX_editX, y)
         if self.edits[QadDynamicInputEditEnum.EDIT_Y].isVisible(): self.edits[QadDynamicInputEditEnum.EDIT_Y].move(x + offsetX_editY, y)

      if self.edits[QadDynamicInputEditEnum.PROMPT_EDIT].isVisible():
         x, y = self.adjustEditPosition(x, y, width, height)
         self.edits[QadDynamicInputEditEnum.PROMPT_EDIT].move(x, y)

      if self.prevPart is not None:
         p1 = None
         offset = (height * 2) * self.canvas.mapSettings().mapUnitsPerPixel()
         gType = self.prevPart.whatIs()

         if gType == "LINE":
            if self.edits[QadDynamicInputEditEnum.EDIT_DIST_PREV_PT].isVisible():
               # used for previous segment length
               p1 = self.prevPart.getStartPt()
               p2 = self.prevPart.getEndPt()
         elif gType == "ARC":
            center = self.prevPart.center
            if self.edits[QadDynamicInputEditEnum.EDIT_ANG_PREV_PT].isVisible():
               # used for arc corner at the end point of the previous part
               p2 = self.prevPart.getEndPt()
               p1 = QgsPointXY(center.x() + self.prevPart.radius, center.y())
               editPt, lineMarkers = self.getPosAndLineMarkerForArc(p1, center, p2, offset, \
                                                                    self.edits[QadDynamicInputEditEnum.EDIT_ANG_PREV_PT])

               if editPt is not None:
                  self.edits[QadDynamicInputEditEnum.EDIT_ANG_PREV_PT].move(editPt.x(), editPt.y())
                  del editPt
               if lineMarkers is not None: # if not zero I draw the marker line by adding a line
                  if qad_utils.ptNear(lineMarkers[0], center):
                     lineMarkers.append(center)
                  else:
                     lineMarkers.insert(0, center)
                  self.edits[QadDynamicInputEditEnum.EDIT_ANG_PREV_PT].setLinesMarker(lineMarkers)
                  del lineMarkers

            if self.edits[QadDynamicInputEditEnum.EDIT_REL_DIST_PREV_PT].isVisible():
               # used for arc radius length at the starting point of the previous part
               p1 = self.prevPart.center
               p2 = self.prevPart.getStartPt()
               editPt, lineMarkers = self.getPosAndLineMarkerForLine(p1, p2, \
                                                                     0, self.edits[QadDynamicInputEditEnum.EDIT_REL_DIST_PREV_PT])
               self.edits[QadDynamicInputEditEnum.EDIT_REL_DIST_PREV_PT].move(editPt.x(), editPt.y())
               del editPt
               # I draw the marker line
               self.edits[QadDynamicInputEditEnum.EDIT_REL_DIST_PREV_PT].setLinesMarker(lineMarkers)
               del lineMarkers

            if self.edits[QadDynamicInputEditEnum.EDIT_DIST_PREV_PT].isVisible():
               # used for arc radius length at the end point of the previous part
               # or radius length at the midpoint if the previous and subsequent parts coincide
               p1 = self.prevPart.center
               # if nextPart and prevPart are equal
               if self.nextPart is not None and self.nextPart == self.prevPart:
                  p2 = self.prevPart.getMiddlePt()
               else:
                  p2 = self.prevPart.getEndPt()
               offset = 0
            else:
               p1 = None


         if p1 is not None:
            editPt, lineMarkers = self.getPosAndLineMarkerForLine(p1, p2, \
                                                                  offset, self.edits[QadDynamicInputEditEnum.EDIT_DIST_PREV_PT])
            self.edits[QadDynamicInputEditEnum.EDIT_DIST_PREV_PT].move(editPt.x(), editPt.y())
            del editPt
            # I draw the marker line
            self.edits[QadDynamicInputEditEnum.EDIT_DIST_PREV_PT].setLinesMarker(lineMarkers)
            del lineMarkers

      if self.nextPart is not None:
         p1 = None
         offset = (height * 2) * self.canvas.mapSettings().mapUnitsPerPixel()
         gType = self.nextPart.whatIs()

         if gType == "LINE":
            if self.edits[QadDynamicInputEditEnum.EDIT_DIST_NEXT_PT].isVisible():
               # used for previous segment length
               p1 = self.nextPart.getStartPt()
               p2 = self.nextPart.getEndPt()
         elif gType == "ARC":
            center = self.nextPart.center
            if self.edits[QadDynamicInputEditEnum.EDIT_ANG_NEXT_PT].isVisible():
               # used for arc corner at the starting point of the next part
               p2 = self.nextPart.getStartPt()
               p1 = QgsPointXY(center.x() + self.nextPart.radius, center.y())
               editPt, lineMarkers = self.getPosAndLineMarkerForArc(p1, center, p2, offset, \
                                                                    self.edits[QadDynamicInputEditEnum.EDIT_ANG_NEXT_PT])

               if editPt is not None:
                  self.edits[QadDynamicInputEditEnum.EDIT_ANG_NEXT_PT].move(editPt.x(), editPt.y())
                  del editPt
               if lineMarkers is not None: # if not zero I draw the marker line by adding a line
                  if qad_utils.ptNear(lineMarkers[0], center):
                     lineMarkers.append(center)
                  else:
                     lineMarkers.insert(0, center)
                  self.edits[QadDynamicInputEditEnum.EDIT_ANG_NEXT_PT].setLinesMarker(lineMarkers)
                  del lineMarkers

            # if nextPart and prevPart are equal
            if self.edits[QadDynamicInputEditEnum.EDIT_REL_ANG_PREV_PT].isVisible():
               # used for total arc angle
               offsetArc = height * self.canvas.mapSettings().mapUnitsPerPixel()
               totalArc = QadArc(self.nextPart)
               totalArc.radius = totalArc.radius + offsetArc
               editPt, lineMarkers = self.getPosAndLineMarkerForArcObj(totalArc, self.edits[QadDynamicInputEditEnum.EDIT_REL_ANG_PREV_PT])
               if editPt is not None:
                  self.edits[QadDynamicInputEditEnum.EDIT_REL_ANG_PREV_PT].move(editPt.x(), editPt.y())
                  del editPt
               if lineMarkers is not None: # if not zero I draw the marker line by adding a line
                  lineMarkers.append(center)
                  lineMarkers.insert(0, center)
                  self.edits[QadDynamicInputEditEnum.EDIT_REL_ANG_PREV_PT].setLinesMarker(lineMarkers)
                  del lineMarkers

            if self.edits[QadDynamicInputEditEnum.EDIT_REL_DIST_NEXT_PT].isVisible():
               # used for arc radius length at the end point of the next part
               p1 = self.nextPart.center
               p2 = self.nextPart.getEndPt()
               editPt, lineMarkers = self.getPosAndLineMarkerForLine(p1, p2, \
                                                                     0, self.edits[QadDynamicInputEditEnum.EDIT_REL_DIST_NEXT_PT])
               self.edits[QadDynamicInputEditEnum.EDIT_REL_DIST_NEXT_PT].move(editPt.x(), editPt.y())
               del editPt
               # I draw the marker line
               self.edits[QadDynamicInputEditEnum.EDIT_REL_DIST_NEXT_PT].setLinesMarker(lineMarkers)
               del lineMarkers

            if self.edits[QadDynamicInputEditEnum.EDIT_DIST_NEXT_PT].isVisible():
               # used for arc radius length at the starting point of the next part
               p1 = self.nextPart.center
               p2 = self.nextPart.getStartPt()
               offset = 0
            else:
               p1 = None

         if p1 is not None:
            editPt, lineMarkers = self.getPosAndLineMarkerForLine(p1, p2, \
                                                                  offset, self.edits[QadDynamicInputEditEnum.EDIT_DIST_NEXT_PT])
            self.edits[QadDynamicInputEditEnum.EDIT_DIST_NEXT_PT].move(editPt.x(), editPt.y())
            del editPt
            # I draw the marker line
            self.edits[QadDynamicInputEditEnum.EDIT_DIST_NEXT_PT].setLinesMarker(lineMarkers)
            del lineMarkers


   # ============================================================================
   # refreshResult
   # ============================================================================
   def refreshResult(self, mousePos = None):
      # calculates the result and returns True if the operation is successful
      # the result is also set in self.resValue and, in string format, in self.resStr
      self.resStr = self.resValue = self.edits[QadDynamicInputEditEnum.CMD_LINE_EDIT].toPlainText()
      return True


   # ============================================================================
   # keyPressEvent
   # ============================================================================
   def keyPressEvent(self, e):
      if self.currentEdit is None:
         return

      if e.key() == Qt.Key_Return or e.key == Qt.Key_Enter:
         msg = self.resStr if self.refreshResult() == True else "" # I recalculate the result and use it in string format
         self.showEvaluateMsg(msg)
      else:
         if e.text() != "":
            self.edits[self.currentEdit].keyPressEvent(e)
            self.show(True)



# ===============================================================================
class QadDynamicEditInput(QadDynamicInput):
# ===============================================================================
#    """
#    Class that handles dynamic input
#    """


   # ============================================================================
   # __init__
   # ============================================================================
   def __init__(self, plugIn, context = QadDynamicInputContextEnum.NONE):
      QadDynamicInput.__init__(self, plugIn)

      self.context = context
      self.prevPoint = None # point used as previous point when typing the points of a new object (in map coordinates)

      self.resPt = QgsPointXY() # resulting point

      self.inputMode = QadInputModeEnum.NONE
      self.inputType = QadInputTypeEnum.NONE
      self.keyWords = []
      self.englishKeyWords = []

      self.initGui()
      # flag that determines whether forcing the visibility of widgets by inserting the coordinates of a point (x,y,z)
      self.forcedCoordWidgetVisib = False


   # ============================================================================
   # setPrevPoint
   # ============================================================================
   def setPrevPoint(self, pt):
      if pt is None:
         if self.prevPoint is not None:
            del self.prevPoint
            self.prevPoint = None
      else:
         if self.prevPoint is None:
            self.prevPoint = QgsPointXY(pt)
         else:
            self.prevPoint.setX(pt.x())
            self.prevPoint.setY(pt.y())


   # ============================================================================
   # removeItems
   # ============================================================================
   def removeItems(self):
      QadDynamicInput.removeItems(self)
      self.setPrevPoint(None)


   # ============================================================================
   # reset
   # ============================================================================
   def reset(self, default = None):
      # the function must not reset self.prevPoint, self.prevPart, self.nextPart
      self.currentEdit = None
      self.forcedCoordWidgetVisib = False

      for i in range(0, len(self.edits), 1):
         self.edits[i].reset()

      self.edits[QadDynamicInputEditEnum.EDIT].inputType = self.inputType
      self.edits[QadDynamicInputEditEnum.EDIT].inputMode = self.inputMode

      # update all control colors
      self.setColors()
      # if there is a default value set it
      if default is not None:
         self.setDefault(default)


   # ============================================================================
   # getInitialNdxEdit
   # ============================================================================
   # returns the position of the initial control
   def getInitialNdxEdit(self):
      if self.inputType & QadInputTypeEnum.STRING or self.inputType & QadInputTypeEnum.BOOL or \
         self.inputType & QadInputTypeEnum.INT or self.inputType & QadInputTypeEnum.LONG or \
         self.inputType & QadInputTypeEnum.FLOAT or self.inputType & QadInputTypeEnum.ANGLE:
         return QadDynamicInputEditEnum.EDIT

      elif self.inputType & QadInputTypeEnum.POINT2D or self.inputType & QadInputTypeEnum.POINT3D:
         # if I need to display coordinate widgets
         if self.isCoordWidgetVisib():
            return QadDynamicInputEditEnum.EDIT_X
         # if I need to show the odds widgets
         elif self.isDimensionalWidgetVisib():
            # if a previous point exists
            if self.prevPoint is not None: # involves inserting a new point at the end of the line
               return QadDynamicInputEditEnum.EDIT_DIST_PREV_PT
            else: # moving a point in grip mode
               if self.dynDiVis == 0 or self.dynDiVis == 1: # only one dimension at a time (0) or two dimensions at a time (1)
                  if self.prevPart is not None and self.prevPart.whatIs() == "LINE":
                     return QadDynamicInputEditEnum.EDIT_DIST_PREV_PT
                  elif self.nextPart is not None and self.nextPart.whatIs() == "LINE":
                     return QadDynamicInputEditEnum.EDIT_DIST_NEXT_PT
               elif self.dynDiVis == 2: # as defined by the dynDiGrip variable
                  if self.dynDiGrip & 1: # resulting elevation (distance from the previous point)
                     if self.prevPart is not None and self.prevPart.whatIs() == "LINE":
                        return QadDynamicInputEditEnum.EDIT_DIST_PREV_PT
                     elif self.nextPart is not None and self.nextPart.whatIs() == "LINE":
                        return QadDynamicInputEditEnum.EDIT_DIST_NEXT_PT
                  elif self.dynDiGrip & 2: # length change dimension (distance from the previous position of the same point)
                     if self.prevPart is not None and self.prevPart.whatIs() == "LINE":
                        return QadDynamicInputEditEnum.EDIT_REL_DIST_PREV_PT
                     elif self.nextPart is not None and self.nextPart.whatIs() == "LINE":
                        return QadDynamicInputEditEnum.EDIT_REL_DIST_NEXT_PT
                  elif self.dynDiGrip & 4: # absolute angle dimension
                     if self.prevPart is not None and self.prevPart.whatIs() == "LINE":
                        return QadDynamicInputEditEnum.EDIT_ANG_PREV_PT
                     elif self.nextPart is not None and self.nextPart.whatIs() == "LINE":
                        return QadDynamicInputEditEnum.EDIT_ANG_NEXT_PT
                  elif self.dynDiGrip & 8: # angle modification dimension (angle relative to the angle with the previous point)
                     if self.prevPart is not None and self.prevPart.whatIs() == "LINE":
                        return QadDynamicInputEditEnum.EDIT_REL_ANG_PREV_PT
                     elif self.nextPart is not None and self.nextPart.whatIs() == "LINE":
                        return QadDynamicInputEditEnum.EDIT_REL_ANG_NEXT_PT

      return None


   # ============================================================================
   # getNextNdxEditSequence
   # ============================================================================
   # returns the position of the next control using the sequence
   def getNextNdxEditSequence(self, currentEdit):
      editSequence = [QadDynamicInputEditEnum.CMD_LINE_EDIT, \
                      QadDynamicInputEditEnum.EDIT, \
                      QadDynamicInputEditEnum.EDIT_X, \
                      QadDynamicInputEditEnum.EDIT_Y, \
                      QadDynamicInputEditEnum.EDIT_Z, \
                      QadDynamicInputEditEnum.EDIT_DIST_PREV_PT, \
                      QadDynamicInputEditEnum.EDIT_ANG_PREV_PT, \
                      QadDynamicInputEditEnum.EDIT_REL_DIST_PREV_PT, \
                      QadDynamicInputEditEnum.EDIT_REL_ANG_PREV_PT, \
                      QadDynamicInputEditEnum.EDIT_DIST_NEXT_PT, \
                      QadDynamicInputEditEnum.EDIT_ANG_NEXT_PT, \
                      QadDynamicInputEditEnum.EDIT_REL_DIST_NEXT_PT, \
                      QadDynamicInputEditEnum.EDIT_REL_ANG_NEXT_PT, \
                      QadDynamicInputEditEnum.EDIT_Z]
      start = i = editSequence.index(currentEdit)
      maxLimit = len(editSequence) - 1
      while True:
         i = 0 if i >= maxLimit else i + 1 # ciclico
         if i == start: break

         # whether dimension widgets are visible as defined by the dynDiGrip variable o
         # the coordinates widgets are being displayed
         # then all widgets are already visible
         if (self.isDimensionalWidgetVisib() == False and self.dynDiVis == 2) or \
            self.isCoordWidgetVisib():
            if self.edits[editSequence[i]].isVisible(): # controllo visibile successivo
               return editSequence[i]
         else:
            if self.isDimensionalWidgetVisib() and self.dynDiVis != 2:
               # involves inserting a new point at the end of the line
               if self.prevPoint is not None:
                  if editSequence[i] == QadDynamicInputEditEnum.EDIT_DIST_PREV_PT or \
                     editSequence[i] == QadDynamicInputEditEnum.EDIT_ANG_PREV_PT:
                     return editSequence[i]
               else: # if you were in grip mode
                  if (self.prevPart is not None and self.prevPart.whatIs() == "LINE" and \
                      (editSequence[i] == QadDynamicInputEditEnum.EDIT_DIST_PREV_PT or \
                       editSequence[i] == QadDynamicInputEditEnum.EDIT_REL_DIST_PREV_PT or \
                       editSequence[i] == QadDynamicInputEditEnum.EDIT_ANG_PREV_PT or \
                       editSequence[i] == QadDynamicInputEditEnum.EDIT_REL_ANG_PREV_PT)) or \
                     (self.nextPart is not None and self.nextPart.whatIs() == "LINE" and \
                      (editSequence[i] == QadDynamicInputEditEnum.EDIT_DIST_NEXT_PT or \
                       editSequence[i]== QadDynamicInputEditEnum.EDIT_REL_DIST_NEXT_PT or \
                       editSequence[i] == QadDynamicInputEditEnum.EDIT_ANG_NEXT_PT or \
                       editSequence[i] == QadDynamicInputEditEnum.EDIT_REL_ANG_NEXT_PT)):
                     return editSequence[i]

      return editSequence[currentEdit]


   # ============================================================================
   # setNextCurrentEdit
   # ============================================================================
   def setNextCurrentEdit(self):
      if self.currentEdit is None: # if it is not set which edit is the current one
         self.setInitialFocus()
         return

      nextEdit = self.getNextNdxEditSequence(self.currentEdit)

      # whether dimension widgets are visible as defined by the dynDiGrip variable o
      # the coordinates widgets are being displayed
      # then all widgets are already visible
      if (self.isDimensionalWidgetVisib() == False and self.dynDiVis == 2) or \
         self.isCoordWidgetVisib():
         self.currentEdit = nextEdit
      else:
         if self.isDimensionalWidgetVisib() and self.dynDiVis != 2:
            if self.dynDiVis == 0: # only one share at a time
               # I turn off the current control
               self.edits[self.currentEdit].show(False)
               self.currentEdit = nextEdit
               # I display the next control
               self.edits[self.currentEdit].show(True)
               self.mouseMoveEvent(self.canvas.mouseLastXY()) # I position the attributes that, being previously turned off, have an out-of-date position
            elif self.dynDiVis == 1: # only two dimensions at a time
               # I turn off the current control
               self.edits[self.currentEdit].show(False)
               self.currentEdit = nextEdit
               nextEdit = self.getNextNdxEditSequence(nextEdit)
               # I display the next control of the next
               self.edits[nextEdit].show(True)
               self.mouseMoveEvent(self.canvas.mouseLastXY()) # I position the attributes that, being previously turned off, have an out-of-date position

      self.setFocus()


   # ============================================================================
   # getPrevNdxEditSequence
   # ============================================================================
   # returns the position of the previous control using the sequence
   def getPrevNdxEditSequence(self, currentEdit):
      editSequence = [QadDynamicInputEditEnum.CMD_LINE_EDIT, \
                      QadDynamicInputEditEnum.EDIT, \
                      QadDynamicInputEditEnum.EDIT_X, \
                      QadDynamicInputEditEnum.EDIT_Y, \
                      QadDynamicInputEditEnum.EDIT_Z, \
                      QadDynamicInputEditEnum.EDIT_DIST_PREV_PT, \
                      QadDynamicInputEditEnum.EDIT_ANG_PREV_PT, \
                      QadDynamicInputEditEnum.EDIT_REL_DIST_PREV_PT, \
                      QadDynamicInputEditEnum.EDIT_REL_ANG_PREV_PT, \
                      QadDynamicInputEditEnum.EDIT_DIST_NEXT_PT, \
                      QadDynamicInputEditEnum.EDIT_ANG_NEXT_PT, \
                      QadDynamicInputEditEnum.EDIT_REL_DIST_NEXT_PT, \
                      QadDynamicInputEditEnum.EDIT_REL_ANG_NEXT_PT, \
                      QadDynamicInputEditEnum.EDIT_Z]
      start = i = editSequence.index(self.currentEdit)
      maxLimit = len(editSequence) - 1
      while True:
         i = maxLimit if i <= 0 else i - 1 # ciclico
         if i == start: break

         # whether dimension widgets are visible as defined by the dynDiGrip variable o
         # the coordinates widgets are being displayed
         # then all widgets are already visible
         if (self.isDimensionalWidgetVisib() == False and self.dynDiVis == 2) or \
            self.isCoordWidgetVisib():
            if self.edits[editSequence[i]].isVisible(): # controllo visibile successivo
               return editSequence[i]
         else:
            if self.isDimensionalWidgetVisib() and self.dynDiVis != 2:
               if self.prevPoint is not None: # involves inserting a new point at the end of the line
                  if editSequence[i] == QadDynamicInputEditEnum.EDIT_DIST_PREV_PT or \
                     editSequence[i] == QadDynamicInputEditEnum.EDIT_ANG_PREV_PT:
                     return editSequence[i]
               else: # if you were in grip mode
                  if (self.prevPart is not None and self.prevPart.whatIs() == "LINE" and \
                      (editSequence[i] == QadDynamicInputEditEnum.EDIT_DIST_PREV_PT or \
                       editSequence[i] == QadDynamicInputEditEnum.EDIT_REL_DIST_PREV_PT or \
                       editSequence[i] == QadDynamicInputEditEnum.EDIT_ANG_PREV_PT or \
                       editSequence[i] == QadDynamicInputEditEnum.EDIT_REL_ANG_PREV_PT)) or \
                     (self.nextPart is not None and self.nextPart.whatIs() == "LINE" and \
                      (editSequence[i] == QadDynamicInputEditEnum.EDIT_DIST_NEXT_PT or \
                       editSequence[i]== QadDynamicInputEditEnum.EDIT_REL_DIST_NEXT_PT or \
                       editSequence[i] == QadDynamicInputEditEnum.EDIT_ANG_NEXT_PT or \
                       editSequence[i] == QadDynamicInputEditEnum.EDIT_REL_ANG_NEXT_PT)):
                     return editSequence[i]

      return editSequence[currentEdit]


   # ============================================================================
   # setPrevCurrentEdit
   # ============================================================================
   def setPrevCurrentEdit(self):
      if self.currentEdit is None: # if it is not set which edit is the current one
         self.setInitialFocus()
         return

      prevEdit = self.getPrevNdxEditSequence(self.currentEdit)

      # whether dimension widgets are visible as defined by the dynDiGrip variable o
      # the coordinates widgets are being displayed
      # then all widgets are already visible
      if (self.isDimensionalWidgetVisib() == False and self.dynDiVis == 2) or \
         self.isCoordWidgetVisib():
         self.currentEdit = prevEdit
      else:
         if self.isDimensionalWidgetVisib() and self.dynDiVis != 2:
            if self.dynDiVis == 0: # only one share at a time
               # I turn off the current control
               self.edits[self.currentEdit].show(False)
               self.currentEdit = prevEdit
               # I display the next control
               self.edits[self.currentEdit].show(True)
               self.mouseMoveEvent(self.canvas.mouseLastXY()) # I position the attributes that, being previously turned off, have an out-of-date position
            elif self.dynDiVis == 1: # only two dimensions at a time
               # I turn off the current control
               self.edits[self.currentEdit].show(False)
               self.currentEdit = prevEdit
               prevEdit = self.getNextNdxEditSequence(prevEdit)
               # I display the previous control of the previous one
               self.edits[prevEdit].show(True)
               self.mouseMoveEvent(self.canvas.mouseLastXY()) # I position the attributes that, being previously turned off, have an out-of-date position

      self.setFocus()


   # ============================================================================
   # isCoordWidgetVisib
   # ============================================================================
   def isCoordWidgetVisib(self):
      # returns whether coordinate widgets should be shown

      # if the refund of a point is not allowed
      if not (self.inputType & QadInputTypeEnum.POINT2D) and not(self.inputType & QadInputTypeEnum.POINT3D):
         return False
      # if the display of coordinates is forced
      if self.forcedCoordWidgetVisib: return True
      # if (there is neither a previous point, a previous part, a subsequent part or the dimension input is not enabled) and the pointer input is enabled or if
      # the display of coordinates is forced
      if (((self.prevPoint is None and self.prevPart is None and self.nextPart is None) or self.isDimensionalInputOn() == False) and \
          self.isPointInputOn()):
         return True
      else:
         return False


   # ============================================================================
   # isDimensionalWidgetVisib
   # ============================================================================
   def isDimensionalWidgetVisib(self):
      # if the refund of a point is not allowed
      if not (self.inputType & QadInputTypeEnum.POINT2D) and not(self.inputType & QadInputTypeEnum.POINT3D):
         return False
      # if height input is not enabled
      if self.isDimensionalInputOn() == False: return False

      # the display of coordinates must not be forced
      if self.forcedCoordWidgetVisib: return False

      # if the generic input widget should be invisible
      if self.inputType & QadInputTypeEnum.STRING or self.inputType & QadInputTypeEnum.BOOL or \
         self.inputType & QadInputTypeEnum.INT or self.inputType & QadInputTypeEnum.LONG or \
         self.inputType & QadInputTypeEnum.FLOAT or self.inputType & QadInputTypeEnum.ANGLE:
         return False

      # if there is a previous point or a previous part or a subsequent part
      if self.prevPoint is not None or self.prevPart is not None or self.nextPart is not None:
         return True
      else:
         return False


   # ============================================================================
   # setDefault
   # ============================================================================
   def setDefault(self, default):
      self.default = default

      # if the result does not depend on the mouse position
      if self.context == QadDynamicInputContextEnum.COMMAND:
         self.edits[QadDynamicInputEditEnum.CMD_LINE_EDIT].showMsg(self.default)

      elif self.inputType & QadInputTypeEnum.STRING or self.inputType & QadInputTypeEnum.BOOL or \
           self.inputType & QadInputTypeEnum.INT or self.inputType & QadInputTypeEnum.LONG or \
           self.inputType & QadInputTypeEnum.FLOAT or self.inputType & QadInputTypeEnum.ANGLE:
         # if it is a number
         if type(self.default) == int or type(self.default) == long or type(self.default) == float:
            if self.inputType & QadInputTypeEnum.ANGLE:
               self.edits[QadDynamicInputEditEnum.EDIT].showMsg(qad_utils.numToStringFmt(qad_utils.toDegrees(self.default)))
            else:
               self.edits[QadDynamicInputEditEnum.EDIT].showMsg(qad_utils.numToStringFmt(self.default))
         # if it is a point
         elif type(self.default) == QgsPointXY:
            self.edits[QadDynamicInputEditEnum.EDIT].showMsg(qad_utils.pointToStringFmt(self.default))
         else:
            self.edits[QadDynamicInputEditEnum.EDIT].showMsg(unicode(self.default))


   # ============================================================================
   # show
   # ============================================================================
   def show(self, mode, mousePos = None, prompt = None, default = None):
      # if it's about making invisible I do it regardless of whether it's active or not
      # (used to manage F12)
      if mode == False:
         self.isVisible = False
         for edit in self.edits:
            edit.show(False)
         return False

      if self.isActive() == False: return False

      # if the mouse position is passed the function
      # resets dynamic input state (errors, fire)
      if mousePos is not None:
         self.reset(default)

      if prompt is not None:
         self.edits[QadDynamicInputEditEnum.PROMPT_EDIT].showMsg(prompt, False, False, False) # without updating the position of the controls

      self.isVisible = True

      visibList = [False] * len(self.edits)

      if self.isPromptActive() and len(self.edits[QadDynamicInputEditEnum.PROMPT_EDIT].toPlainText()) > 0:
         visibList[QadDynamicInputEditEnum.PROMPT_EDIT] = True

      # whether it requires a real number or an angle e
      # the display of coordinates is not forced
      if (self.inputType & QadInputTypeEnum.FLOAT or self.inputType & QadInputTypeEnum.ANGLE) and \
            not self.forcedCoordWidgetVisib:
         visibList[QadDynamicInputEditEnum.EDIT] = True

      # if I need to display coordinate widgets
      elif self.isCoordWidgetVisib():
         if self.edits[QadDynamicInputEditEnum.EDIT_SYMBOL_COORD_TYPE].toPlainText() != "":
            visibList[QadDynamicInputEditEnum.EDIT_SYMBOL_COORD_TYPE] = True

         visibList[QadDynamicInputEditEnum.EDIT_X] = True
         visibList[QadDynamicInputEditEnum.EDIT_Y] = True
         if self.inputType & QadInputTypeEnum.POINT3D:
            visibList[QadDynamicInputEditEnum.EDIT_Z] = True
      # if I need to show the odds widgets
      elif self.isDimensionalWidgetVisib():
         if self.prevPoint is not None: # involves inserting a new point at the end of the line
            if self.dynDiVis == 0: # only one share at a time
               if self.currentEdit is None:
                  visibList[self.getInitialNdxEdit()] = True
               else:
                  visibList[self.currentEdit] = True
            else:
               visibList[QadDynamicInputEditEnum.EDIT_DIST_PREV_PT] = True
               visibList[QadDynamicInputEditEnum.EDIT_ANG_PREV_PT] = True
         else: # moving a point in grip mode
            if self.dynDiVis == 0: # only one share at a time
               if self.currentEdit is None:
                  first = self.getInitialNdxEdit()
               else:
                  first = self.currentEdit

               if first is not None:
                  visibList[first] = True

            elif self.dynDiVis == 1: # only two dimensions at a time
               if self.currentEdit is None:
                  first = self.getInitialNdxEdit()
               else:
                  first = self.currentEdit

               if first is not None:
                  visibList[first] = True
                  second = self.getNextNdxEditSequence(first)
                  if second is not None:
                     visibList[second] = True

            elif self.dynDiVis == 2: # as defined by the dynDiGrip variable
               if self.dynDiGrip & 1: # resulting elevation (distance from the previous point)
                  if self.prevPart is not None and self.prevPart.whatIs() == "LINE":
                     visibList[QadDynamicInputEditEnum.EDIT_DIST_PREV_PT] = True
                  if self.nextPart is not None and self.nextPart.whatIs() == "LINE":
                     visibList[QadDynamicInputEditEnum.EDIT_DIST_NEXT_PT] = True
               if self.dynDiGrip & 2: # length change dimension (distance from the previous position of the same point)
                  if self.prevPart is not None and self.prevPart.whatIs() == "LINE":
                     visibList[QadDynamicInputEditEnum.EDIT_REL_DIST_PREV_PT] = True
                  if self.nextPart is not None and self.nextPart.whatIs() == "LINE":
                     visibList[QadDynamicInputEditEnum.EDIT_REL_DIST_NEXT_PT] = True
               if self.dynDiGrip & 4: # absolute angle dimension
                  if self.prevPart is not None and self.prevPart.whatIs() == "LINE":
                     visibList[QadDynamicInputEditEnum.EDIT_ANG_PREV_PT] = True
                  if self.nextPart is not None and self.nextPart.whatIs() == "LINE":
                     visibList[QadDynamicInputEditEnum.EDIT_ANG_NEXT_PT] = True
               if self.dynDiGrip & 8: # angle modification dimension (angle relative to the angle with the previous point)
                  if self.prevPart is not None and self.prevPart.whatIs() == "LINE":
                     visibList[QadDynamicInputEditEnum.EDIT_REL_ANG_PREV_PT] = True
                  if self.nextPart is not None and self.nextPart.whatIs() == "LINE":
                     visibList[QadDynamicInputEditEnum.EDIT_REL_ANG_NEXT_PT] = True

#             # exception for this flag which is considered regardless of the value of self.dynDiVis
#             if self.dynDiGrip & 16: # radius length
#                if self.prevPart is not None and self.prevPart.whatIs() == "ARC":
#                   # used for radius length at the end point of the previous part
#                   # or radius length at midpoint if previous and following part are the same arc
#                   visibList[QadDynamicInputEditEnum.EDIT_DIST_PREV_PT] = True
#                   # used for radius length at the starting point of the previous part
#                   visibList[QadDynamicInputEditEnum.EDIT_REL_DIST_PREV_PT] = True
#                if self.nextPart is not None and self.nextPart.whatIs() == "ARC":
#                   # if nextPart and prevPart are equal
#                   if self.prevPart is not None and self.nextPart == self.prevPart:
#                      # used for radius length at the starting point of the previous part
#                      visibList[QadDynamicInputEditEnum.EDIT_REL_DIST_PREV_PT] = False
#                   else:
#                      # used for radius length at starting point of next part
#                      visibList[QadDynamicInputEditEnum.EDIT_DIST_NEXT_PT] = True
#                      # used for radius length at the end point of the next part
#                      visibList[QadDynamicInputEditEnum.EDIT_REL_DIST_NEXT_PT] = True


      elif self.inputType & QadInputTypeEnum.STRING or self.inputType & QadInputTypeEnum.BOOL or \
           self.inputType & QadInputTypeEnum.INT or self.inputType & QadInputTypeEnum.LONG or \
           self.inputType & QadInputTypeEnum.FLOAT or self.inputType & QadInputTypeEnum.ANGLE:
         visibList[QadDynamicInputEditEnum.EDIT] = True

      for i in range(0, len(self.edits), 1):
         self.edits[i].show(visibList[i])

      self.setFocus()

      # riposiziono i widget
      if mousePos is None:
         self.mouseMoveEvent(self.canvas.mouseLastXY())
      else:
         self.mouseMoveEvent(mousePos)

      return self.isVisible


   # ============================================================================
   # showErr
   # ============================================================================
   def showErr(self, err = ""):
      if self.isActive() == False: return

      if self.currentEdit is not None:
         self.edits[self.currentEdit].error = True
         self.edits[self.currentEdit].setColors() # recolors with red borders because error=True

      self.moveCtrls() # to reposition the controls


   # ============================================================================
   # showInputMsg
   # ============================================================================
   def showInputMsg(self, inputMsg = None, inputType = QadInputTypeEnum.COMMAND, \
                    default = None, keyWords = "", inputMode = QadInputModeEnum.NONE):
      if self.isActive() == False: return False

      # context must be initialized first by the command
      self.inputType = inputType
      self.inputMode = inputMode
      self.keyWords = []
      self.englishKeyWords = []

      if (keyWords is not None) and len(keyWords) > 0:
         # separator character between local language and English keywords
         localEnglishKeyWords = keyWords.split("_")
         self.keyWords = localEnglishKeyWords[0].split("/") # carattere separatore delle parole chiave
         if len(localEnglishKeyWords) > 1:
            self.englishKeyWords = localEnglishKeyWords[1].split("/") # carattere separatore delle parole chiave
         else:
            del self.englishKeyWords[:]

         initial = inputMsg.find("[")
         self.show(True, self.canvas.mouseLastXY(), inputMsg[0:initial], default) # resetta tutto
      else:
         self.show(True, self.canvas.mouseLastXY(), inputMsg, default) # resetta tutto


   # ============================================================================
   # mouseMoveEvent
   # ============================================================================
   def mouseMoveEvent(self, mousePos):
      if self.isActive() == False or self.isVisible == False: return

      self.refreshResult(mousePos)

      # if coordinate widgets are visible
      if self.edits[QadDynamicInputEditEnum.EDIT_X].isVisible():
         if self.prevPoint is None: # if it is not set in the dynamic input I look for it in the plugin (which refreshResult also does)
            if self.plugIn.lastPoint is None:
               prevPt = QgsPointXY(0,0)
            else:
               prevPt = self.plugIn.lastPoint
         else:
            prevPt = self.prevPoint

         # if they are relative coordinates
         relative = True if self.dynPiCoords == 0 else False
         # if they are polar coordinates
         polar = True if self.dynPiFormat == 0 else False
         if self.edits[QadDynamicInputEditEnum.EDIT_SYMBOL_COORD_TYPE].isVisible():
            coordType = self.edits[QadDynamicInputEditEnum.EDIT_SYMBOL_COORD_TYPE].toPlainText()
            if "@" in coordType: relative = True
            elif "#" in coordType: relative = False
            polar = True if "<" in coordType else False
         else: # if it is not explicit that it is relative but it is because of dynPiCoords
            prevPt = self.prevPoint # if there is no previous point set in the dynamic input
            if prevPt is None:
               relative = False
               polar = False

         if polar == False: # if they are Cartesian coordinates
            if self.edits[QadDynamicInputEditEnum.EDIT_X].isLockedValue() == False:
               # if they are relative coordinates
               if relative:
                  self.edits[QadDynamicInputEditEnum.EDIT_X].showMsg(qad_utils.numToStringFmt(self.resPt.x() - prevPt.x()), False, False, False) # without updating the position of the controls
               else:
                  self.edits[QadDynamicInputEditEnum.EDIT_X].showMsg(qad_utils.numToStringFmt(self.resPt.x()), False, False, False) # without updating the position of the controls

            if self.edits[QadDynamicInputEditEnum.EDIT_Y].isLockedValue() == False:
               # if they are relative coordinates
               if relative:
                  self.edits[QadDynamicInputEditEnum.EDIT_Y].showMsg(qad_utils.numToStringFmt(self.resPt.y() - prevPt.y()), False, False, False) # without updating the position of the controls
               else:
                  self.edits[QadDynamicInputEditEnum.EDIT_Y].showMsg(qad_utils.numToStringFmt(self.resPt.y()), False, False, False) # without updating the position of the controls

            if self.edits[QadDynamicInputEditEnum.EDIT_Z].isVisible() and \
               self.edits[QadDynamicInputEditEnum.EDIT_Z].isLockedValue() == False:
                  # if they are relative coordinates
                  if relative:
                     self.edits[QadDynamicInputEditEnum.EDIT_Z].showMsg(qad_utils.numToStringFmt(self.resPt.z() - prevPt.z()), False, False, False) # without updating the position of the controls
                  else:
                     self.edits[QadDynamicInputEditEnum.EDIT_Z].showMsg(qad_utils.numToStringFmt(self.resPt.z()), False, False, False) # without updating the position of the controls
         elif prevPt is not None: # coordinate polari
            # in the case of polar coordinates EDIT_X contains the distance from the previous point or from 0.0
            if self.edits[QadDynamicInputEditEnum.EDIT_X].isLockedValue() == False:
               if relative:
                  dist = qad_utils.getDistance(prevPt, self.resPt)
               else:
                  dist = qad_utils.getDistance(QgsPointXY(0, 0), self.resPt)
               self.edits[QadDynamicInputEditEnum.EDIT_X].showMsg(qad_utils.numToStringFmt(dist), False, False, False) # without updating the position of the controls

            # in the case of polar coordinates EDIT_Y contains the angle
            if self.edits[QadDynamicInputEditEnum.EDIT_Y].isLockedValue() == False:
               if relative:
                  angle = qad_utils.getAngleBy2Pts(prevPt, self.resPt, 0) # without tolerance
               else:
                  angle = qad_utils.getAngleBy2Pts(QgsPointXY(0, 0), self.resPt, 0) # without tolerance

               self.edits[QadDynamicInputEditEnum.EDIT_Y].showMsg(qad_utils.numToStringFmt(qad_utils.toDegrees(angle)), False, False, False) # without updating the position of the controls

      # if the "distance from previous point" dimensions widget is visible
      if self.edits[QadDynamicInputEditEnum.EDIT_DIST_PREV_PT].isVisible() and \
         self.edits[QadDynamicInputEditEnum.EDIT_DIST_PREV_PT].isLockedValue() == False:
         if self.prevPoint is not None: # involves inserting a new point at the end of the line
            dist = qad_utils.getDistance(self.prevPoint, self.resPt)
            self.edits[QadDynamicInputEditEnum.EDIT_DIST_PREV_PT].showMsg(qad_utils.numToStringFmt(dist), False, False, False) # without updating the position of the controls
         elif self.prevPart is not None:
            gType = self.prevPart.whatIs()

            if gType == "LINE": # moving a point of a segment in grip mode
               dist = qad_utils.getDistance(self.prevPart.getStartPt(), self.resPt)
               self.edits[QadDynamicInputEditEnum.EDIT_DIST_PREV_PT].showMsg(qad_utils.numToStringFmt(dist), False, False, False) # without updating the position of the controls
            elif gType == "ARC": # moving a point of an arc in grip mode
               # used for radius length at the end point of the previous part
               # or radius length at the midpoint if the previous and following part are the same arc
               self.edits[QadDynamicInputEditEnum.EDIT_DIST_PREV_PT].showMsg(qad_utils.numToStringFmt(self.prevPart.radius), False, False, False) # without updating the position of the controls

      # if the "angle from previous point" dimensions widget is visible
      if self.edits[QadDynamicInputEditEnum.EDIT_ANG_PREV_PT].isVisible() and \
         self.edits[QadDynamicInputEditEnum.EDIT_ANG_PREV_PT].isLockedValue() == False:
         if self.prevPoint is not None: # involves inserting a new point at the end of the line
            angle = qad_utils.getAngleBy2Pts(self.prevPoint, self.resPt, 0) # without tolerance
            if angle >= math.pi and angle < 2 * math.pi:
               angle = 2 * math.pi - angle
            self.edits[QadDynamicInputEditEnum.EDIT_ANG_PREV_PT].showMsg(qad_utils.numToStringFmt(qad_utils.toDegrees(angle)), False, False, False) # without updating the position of the controls
         elif self.prevPart is not None and self.prevPart.whatIs() == "LINE": # moving a point of a segment in grip mode
            angle = qad_utils.getAngleBy2Pts(self.prevPart.getStartPt(), self.resPt, 0) # without tolerance
            if angle >= math.pi and angle < 2 * math.pi:
               angle = 2 * math.pi - angle
            self.edits[QadDynamicInputEditEnum.EDIT_ANG_PREV_PT].showMsg(qad_utils.numToStringFmt(qad_utils.toDegrees(angle)), False, False, False) # without updating the position of the controls

      # if the dimensions widget in grip mode "distance from the previous position of the same point in the direction from the previous point" is visible
      if self.edits[QadDynamicInputEditEnum.EDIT_REL_DIST_PREV_PT].isVisible() and \
         self.edits[QadDynamicInputEditEnum.EDIT_REL_DIST_PREV_PT].isLockedValue() == False:
         if self.prevPart is not None:
            gType = self.prevPart.whatIs()

            if gType == "LINE": # moving a point of a segment in grip mode
               dist = qad_utils.getDistance(self.prevPart.getEndPt(), self.resPt)
               self.edits[QadDynamicInputEditEnum.EDIT_REL_DIST_PREV_PT].showMsg(qad_utils.numToStringFmt(dist), False, False, False) # without updating the position of the controls
            elif gType == "ARC": # moving a point of an arc in grip mode
               # used for radius length at the starting point of the previous part if arc
               self.edits[QadDynamicInputEditEnum.EDIT_REL_DIST_PREV_PT].showMsg(qad_utils.numToStringFmt(self.prevPart.radius), False, False, False) # without updating the position of the controls

      # if the dimensions widget in grip mode "angle relative to angle from previous point" is visible
      if self.edits[QadDynamicInputEditEnum.EDIT_REL_ANG_PREV_PT].isVisible() and \
         self.edits[QadDynamicInputEditEnum.EDIT_REL_ANG_PREV_PT].isLockedValue() == False:
         if self.prevPart is not None and self.prevPart.whatIs() == "LINE": # moving a point of a segment in grip mode
            pt1 = self.prevPart.getStartPt()
            pt2 = self.prevPart.getEndPt()
            anglePart = qad_utils.getAngleBy2Pts(pt1, pt2, 0) # without tolerance
            angleMouse = qad_utils.getAngleBy2Pts(pt1, self.resPt, 0) # without tolerance
            angle = qad_utils.normalizeAngle(angleMouse - anglePart)
            # if the mouse forms an angle between 180 and 360 then the angle entered must be subtracted from 360 degrees
            if angle >= math.pi and angle < (2 * math.pi):
               angle = (2 * math.pi) - angle
            self.edits[QadDynamicInputEditEnum.EDIT_REL_ANG_PREV_PT].showMsg(qad_utils.numToStringFmt(qad_utils.toDegrees(angle)), False, False, False) # without updating the position of the controls

      # if the dimensions widget in grip mode "distance to next point" is visible
      if self.edits[QadDynamicInputEditEnum.EDIT_DIST_NEXT_PT].isVisible() and \
         self.edits[QadDynamicInputEditEnum.EDIT_DIST_NEXT_PT].isLockedValue() == False:
         if self.nextPart is not None:
            gType = self.nextPart.whatIs()
            if gType == "LINE": # moving a point of a segment in grip mode
               dist = qad_utils.getDistance(self.nextPart.getEndPt(), self.resPt)
               self.edits[QadDynamicInputEditEnum.EDIT_DIST_NEXT_PT].showMsg(qad_utils.numToStringFmt(dist), False, False, False) # without updating the position of the controls
            elif gType == "ARC": # moving a point of an arc in grip mode
               # used for radius length at the starting point of the next part if arc
               self.edits[QadDynamicInputEditEnum.EDIT_DIST_NEXT_PT].showMsg(qad_utils.numToStringFmt(self.nextPart.radius), False, False, False) # without updating the position of the controls

      # if the dimensions widget in grip mode "distance from the previous position of the same point in the direction from the next point" is visible
      if self.edits[QadDynamicInputEditEnum.EDIT_REL_DIST_NEXT_PT].isVisible() and \
         self.edits[QadDynamicInputEditEnum.EDIT_REL_DIST_NEXT_PT].isLockedValue() == False:
         if self.nextPart is not None:
            gType = self.nextPart.whatIs()

            if gType == "LINE": # moving a point of a segment in grip mode
               dist = qad_utils.getDistance(self.nextPart.getStartPt(), self.resPt)
               self.edits[QadDynamicInputEditEnum.EDIT_REL_DIST_NEXT_PT].showMsg(qad_utils.numToStringFmt(dist), False, False, False) # without updating the position of the controls
            elif gType == "ARC": # moving a point of an arc in grip mode
               # used for radius length at the end point of the next part if arc
               self.edits[QadDynamicInputEditEnum.EDIT_REL_DIST_NEXT_PT].showMsg(qad_utils.numToStringFmt(self.nextPart.radius), False, False, False) # without updating the position of the controls

      # if the "angle from next point" dimensions widget is visible
      if self.edits[QadDynamicInputEditEnum.EDIT_ANG_NEXT_PT].isVisible() and \
         self.edits[QadDynamicInputEditEnum.EDIT_ANG_NEXT_PT].isLockedValue() == False:
         if self.nextPart is not None and self.nextPart.whatIs() == "LINE": # moving a point of a segment in grip mode
            angle = qad_utils.getAngleBy2Pts(self.nextPart.getEndPt(), self.resPt, 0) # without tolerance
            if angle >= math.pi and angle < 2 * math.pi:
               angle = 2 * math.pi - angle
            self.edits[QadDynamicInputEditEnum.EDIT_ANG_NEXT_PT].showMsg(qad_utils.numToStringFmt(qad_utils.toDegrees(angle)), False, False, False) # without updating the position of the controls

      # if the dimensions widget in grip mode "distance from previous point" is visible
      if self.edits[QadDynamicInputEditEnum.EDIT_REL_ANG_NEXT_PT].isVisible() and \
         self.edits[QadDynamicInputEditEnum.EDIT_REL_ANG_NEXT_PT].isLockedValue() == False:
         if self.nextPart is not None and self.nextPart.whatIs() == "LINE": # moving a point of a segment in grip mode
            pt1 = self.nextPart.getEndPt()
            pt2 = self.nextPart.getStartPt()
            anglePart = qad_utils.getAngleBy2Pts(pt1, pt2, 0) # without tolerance
            angleMouse = qad_utils.getAngleBy2Pts(pt1, self.resPt, 0) # without tolerance
            angle = qad_utils.normalizeAngle(angleMouse - anglePart)
            # if the mouse forms an angle between 180 and 360 then the angle entered must be subtracted from 360 degrees
            if angle >= math.pi and angle < (2 * math.pi):
               angle = (2 * math.pi) - angle
            self.edits[QadDynamicInputEditEnum.EDIT_REL_ANG_NEXT_PT].showMsg(qad_utils.numToStringFmt(qad_utils.toDegrees(angle)), False, False, False) # without updating the position of the controls


      if self.edits[QadDynamicInputEditEnum.EDIT].isVisible() and \
         self.edits[QadDynamicInputEditEnum.EDIT].isLockedValue() == False and \
         self.resValue is not None:
         if self.inputType & QadInputTypeEnum.ANGLE:
            self.edits[QadDynamicInputEditEnum.EDIT].showMsg(qad_utils.numToStringFmt(qad_utils.toDegrees(self.resValue)), False, False, False) # without updating the position of the controls
         elif self.inputType & QadInputTypeEnum.FLOAT:
            self.edits[QadDynamicInputEditEnum.EDIT].showMsg(qad_utils.numToStringFmt(self.resValue), False, False, False) # without updating the position of the controls
         elif self.inputType & QadInputTypeEnum.STRING or self.inputType & QadInputTypeEnum.BOOL or \
              self.inputType & QadInputTypeEnum.INT or self.inputType & QadInputTypeEnum.LONG:
            self.edits[QadDynamicInputEditEnum.EDIT].showMsg(unicode(self.resValue), False, False, False) # without updating the position of the controls

      if self.currentEdit is not None:
         self.edits[self.currentEdit].focusInEvent(None) # I bring the focus back to the current control

      self.moveCtrls(mousePos)

      return


   # ============================================================================
   # moveCtrls
   # ============================================================================
   def moveCtrls(self, mousePos = None):
      # move all visible widgets depending on the context
      if mousePos is not None:
         self.mousePos.setX(mousePos.x())
         self.mousePos.setY(mousePos.y())

      height = self.edits[QadDynamicInputEditEnum.PROMPT_EDIT].height()
      offset = 5

      width = 0
      if self.edits[QadDynamicInputEditEnum.PROMPT_EDIT].isVisible():
         width += self.edits[QadDynamicInputEditEnum.PROMPT_EDIT].width()

      x = self.mousePos.x() + height
      y = self.mousePos.y() + height

      # if you are requesting a point via any of its coordinates
      if self.edits[QadDynamicInputEditEnum.EDIT_X].isVisible() or \
         self.edits[QadDynamicInputEditEnum.EDIT_Y].isVisible() or \
         self.edits[QadDynamicInputEditEnum.EDIT_Z].isVisible():

         if self.edits[QadDynamicInputEditEnum.EDIT_SYMBOL_COORD_TYPE].isVisible():
            if width > 0 : width += offset
            offsetX_editSymbolCoord = width
            width += self.edits[QadDynamicInputEditEnum.EDIT_SYMBOL_COORD_TYPE].width()
         if self.edits[QadDynamicInputEditEnum.EDIT_X].isVisible():
            if width > 0 : width += offset
            offsetX_editX = width
            width += self.edits[QadDynamicInputEditEnum.EDIT_X].width()
         if self.edits[QadDynamicInputEditEnum.EDIT_Y].isVisible():
            if width > 0 : width += offset
            offsetX_editY = width
            width += self.edits[QadDynamicInputEditEnum.EDIT_Y].width()
         if self.edits[QadDynamicInputEditEnum.EDIT_Z].isVisible():
            if width > 0 : width += offset
            offsetX_editZ = width
            width += self.edits[QadDynamicInputEditEnum.EDIT_Z].width()

         x, y = self.adjustEditPosition(x, y, width, height)

         if self.edits[QadDynamicInputEditEnum.EDIT_SYMBOL_COORD_TYPE].isVisible(): self.edits[QadDynamicInputEditEnum.EDIT_SYMBOL_COORD_TYPE].move(x + offsetX_editSymbolCoord, y)
         if self.edits[QadDynamicInputEditEnum.EDIT_X].isVisible(): self.edits[QadDynamicInputEditEnum.EDIT_X].move(x + offsetX_editX, y)
         if self.edits[QadDynamicInputEditEnum.EDIT_Y].isVisible(): self.edits[QadDynamicInputEditEnum.EDIT_Y].move(x + offsetX_editY, y)
         if self.edits[QadDynamicInputEditEnum.EDIT_Z].isVisible(): self.edits[QadDynamicInputEditEnum.EDIT_Z].move(x + offsetX_editZ, y)

      elif self.inputType & QadInputTypeEnum.STRING or self.inputType & QadInputTypeEnum.BOOL or \
           self.inputType & QadInputTypeEnum.INT or self.inputType & QadInputTypeEnum.LONG or \
           self.inputType & QadInputTypeEnum.FLOAT:
         if self.edits[QadDynamicInputEditEnum.EDIT].isVisible():
            if width > 0 : width += offset
            offsetX_edit = width
            width += self.edits[QadDynamicInputEditEnum.EDIT].width()

         x, y = self.adjustEditPosition(x, y, width, height)

         if self.edits[QadDynamicInputEditEnum.EDIT].isVisible(): self.edits[QadDynamicInputEditEnum.EDIT].move(x + offsetX_edit, y)

      elif self.inputType & QadInputTypeEnum.ANGLE:
         if self.edits[QadDynamicInputEditEnum.EDIT].isVisible():
            if self.prevPoint is not None: # involves inserting a new point at the end of the line
               point = self.resPt # posizione
               start = QgsPointXY(self.prevPoint.x() + qad_utils.getDistance(self.prevPoint, point), self.prevPoint.y())
               editPt, lineMarkers = self.getPosAndLineMarkerForArc(start, self.prevPoint, point, 0, \
                                                                    self.edits[QadDynamicInputEditEnum.EDIT])
               if editPt is not None:
                  self.edits[QadDynamicInputEditEnum.EDIT].move(editPt.x(), editPt.y())
                  del editPt
               if lineMarkers is not None: # if not zero I draw the marker line
                  self.edits[QadDynamicInputEditEnum.EDIT].setLinesMarker(lineMarkers)
                  del lineMarkers
            else:
               if width > 0 : width += offset
               offsetX_edit = width
               width += self.edits[QadDynamicInputEditEnum.EDIT].width()
               x, y = self.adjustEditPosition(x, y, width, height)
               self.edits[QadDynamicInputEditEnum.EDIT].move(x + offsetX_edit, y)

      # if I need to show the odds widgets
      elif self.isDimensionalWidgetVisib():
         if self.edits[QadDynamicInputEditEnum.PROMPT_EDIT].isVisible():
            x, y = self.adjustEditPosition(x, y, width, height)
         point = self.resPt # posizione

         if self.prevPoint is not None: # involves inserting a new point at the end of the line
            prevPt = self.prevPoint
         elif self.prevPart is not None and self.prevPart.whatIs() == "LINE": # moving a point of a segment in grip mode
            prevPt = self.prevPart.getStartPt()
         else:
            prevPt = None

         if prevPt is not None:
            if self.edits[QadDynamicInputEditEnum.EDIT_DIST_PREV_PT].isVisible():
               offset = (height * 2) * self.canvas.mapSettings().mapUnitsPerPixel()
               editPt, lineMarkers = self.getPosAndLineMarkerForLine(prevPt, point, \
                                                                     offset, self.edits[QadDynamicInputEditEnum.EDIT_DIST_PREV_PT])
               self.edits[QadDynamicInputEditEnum.EDIT_DIST_PREV_PT].move(editPt.x(), editPt.y())
               del editPt
               # I draw the marker line
               self.edits[QadDynamicInputEditEnum.EDIT_DIST_PREV_PT].setLinesMarker(lineMarkers)
               del lineMarkers

            if self.edits[QadDynamicInputEditEnum.EDIT_ANG_PREV_PT].isVisible():
               start = QgsPointXY(prevPt.x() + qad_utils.getDistance(prevPt, point), prevPt.y())
               editPt, lineMarkers = self.getPosAndLineMarkerForArc(start, prevPt, point, 0, \
                                                                    self.edits[QadDynamicInputEditEnum.EDIT_ANG_PREV_PT])
               if editPt is not None:
                  self.edits[QadDynamicInputEditEnum.EDIT_ANG_PREV_PT].move(editPt.x(), editPt.y())
                  del editPt
               if lineMarkers is not None: # if not zero I draw the marker line
                  self.edits[QadDynamicInputEditEnum.EDIT_ANG_PREV_PT].setLinesMarker(lineMarkers)
                  del lineMarkers

         if self.prevPart is not None:
            gType = self.prevPart.whatIs()
            if gType == "LINE": # moving a point of a segment in grip mode
               prevCurrentPt = self.prevPart.getEndPt()
               angle = qad_utils.getAngleBy2Pts(prevPt, point, 0) # without tolerance
               pt = qad_utils.getPolarPointByPtAngle(prevPt, angle, self.prevPart.length())
               if self.edits[QadDynamicInputEditEnum.EDIT_REL_DIST_PREV_PT].isVisible():
                  offset = (height * 1) * self.canvas.mapSettings().mapUnitsPerPixel()
                  editPt, lineMarkers = self.getPosAndLineMarkerForLine(pt, point, \
                                                                        offset, self.edits[QadDynamicInputEditEnum.EDIT_REL_DIST_PREV_PT])
                  self.edits[QadDynamicInputEditEnum.EDIT_REL_DIST_PREV_PT].move(editPt.x(), editPt.y())
                  del editPt
                  # I draw the marker line
                  self.edits[QadDynamicInputEditEnum.EDIT_REL_DIST_PREV_PT].setLinesMarker(lineMarkers)
                  del lineMarkers

               if self.edits[QadDynamicInputEditEnum.EDIT_REL_ANG_PREV_PT].isVisible():
                  editPt, lineMarkers = self.getPosAndLineMarkerForArc(prevCurrentPt, prevPt, pt, 0, \
                                                                       self.edits[QadDynamicInputEditEnum.EDIT_ANG_PREV_PT], True) # LineMarker arc only
                  self.edits[QadDynamicInputEditEnum.EDIT_REL_ANG_PREV_PT].move(editPt.x(), editPt.y())
                  del editPt
                  # I draw the marker line
                  self.edits[QadDynamicInputEditEnum.EDIT_REL_ANG_PREV_PT].setLinesMarker(lineMarkers)
                  del lineMarkers
            elif gType == "ARC": # moving a point of an arc in grip mode
               center = self.prevPart.center

               if self.edits[QadDynamicInputEditEnum.EDIT_DIST_PREV_PT].isVisible():
                  # used for arc radius length at the end point of the previous part
                  # or radius length at the midpoint if the previous and subsequent parts coincide
                  if self.nextPart is not None and self.nextPart == self.prevPart:
                     p2 = self.prevPart.getMiddlePt()
                  else:
                     p2 = self.prevPart.getEndPt()

                  editPt, lineMarkers = self.getPosAndLineMarkerForLine(center, p2, \
                                                                        0, self.edits[QadDynamicInputEditEnum.EDIT_DIST_PREV_PT])
                  self.edits[QadDynamicInputEditEnum.EDIT_DIST_PREV_PT].move(editPt.x(), editPt.y())
                  del editPt
                  # I draw the marker line
                  self.edits[QadDynamicInputEditEnum.EDIT_DIST_PREV_PT].setLinesMarker(lineMarkers)
                  del lineMarkers

               if self.edits[QadDynamicInputEditEnum.EDIT_REL_DIST_PREV_PT].isVisible():
                  # used for arc radius length at the starting point of the previous part
                  p2 = self.prevPart.getStartPt()
                  editPt, lineMarkers = self.getPosAndLineMarkerForLine(center, p2, \
                                                                        0, self.edits[QadDynamicInputEditEnum.EDIT_REL_DIST_PREV_PT])
                  self.edits[QadDynamicInputEditEnum.EDIT_REL_DIST_PREV_PT].move(editPt.x(), editPt.y())
                  del editPt
                  # I draw the marker line
                  self.edits[QadDynamicInputEditEnum.EDIT_REL_DIST_PREV_PT].setLinesMarker(lineMarkers)
                  del lineMarkers

         if self.nextPart is not None:
            gType = self.nextPart.whatIs()
            if gType == "LINE": # moving a point of a segment in grip mode
               nextPt = self.nextPart.getEndPt()
               if self.edits[QadDynamicInputEditEnum.EDIT_DIST_NEXT_PT].isVisible():
                  offset = (height * 2) * self.canvas.mapSettings().mapUnitsPerPixel()
                  editPt, lineMarkers = self.getPosAndLineMarkerForLine(nextPt, point, \
                                                                        offset, self.edits[QadDynamicInputEditEnum.EDIT_DIST_PREV_PT])
                  self.edits[QadDynamicInputEditEnum.EDIT_DIST_NEXT_PT].move(editPt.x(), editPt.y())
                  del editPt
                  # I draw the marker line
                  self.edits[QadDynamicInputEditEnum.EDIT_DIST_NEXT_PT].setLinesMarker(lineMarkers)
                  del lineMarkers

               if self.edits[QadDynamicInputEditEnum.EDIT_ANG_NEXT_PT].isVisible():
                  start = QgsPointXY(nextPt.x() + qad_utils.getDistance(nextPt, point), nextPt.y())
                  editPt, lineMarkers = self.getPosAndLineMarkerForArc(start, nextPt, point, 0, \
                                                                       self.edits[QadDynamicInputEditEnum.EDIT_ANG_NEXT_PT])
                  if editPt is not None:
                     self.edits[QadDynamicInputEditEnum.EDIT_ANG_NEXT_PT].move(editPt.x(), editPt.y())
                     del editPt
                  if lineMarkers is not None: # if not zero I draw the marker line
                     self.edits[QadDynamicInputEditEnum.EDIT_ANG_NEXT_PT].setLinesMarker(lineMarkers)
                     del lineMarkers

               prevCurrentPt = self.nextPart.getStartPt()
               angle = qad_utils.getAngleBy2Pts(nextPt, point, 0) # without tolerance
               pt = qad_utils.getPolarPointByPtAngle(nextPt, angle, self.nextPart.length())
               if self.edits[QadDynamicInputEditEnum.EDIT_REL_DIST_NEXT_PT].isVisible():
                  offset = (height * 1) * self.canvas.mapSettings().mapUnitsPerPixel()
                  editPt, lineMarkers = self.getPosAndLineMarkerForLine(pt, point, \
                                                                        offset, self.edits[QadDynamicInputEditEnum.EDIT_REL_DIST_NEXT_PT])
                  self.edits[QadDynamicInputEditEnum.EDIT_REL_DIST_NEXT_PT].move(editPt.x(), editPt.y())
                  del editPt
                  # I draw the marker line
                  self.edits[QadDynamicInputEditEnum.EDIT_REL_DIST_NEXT_PT].setLinesMarker(lineMarkers)
                  del lineMarkers

               if self.edits[QadDynamicInputEditEnum.EDIT_REL_ANG_NEXT_PT].isVisible():
                  editPt, lineMarkers = self.getPosAndLineMarkerForArc(prevCurrentPt, nextPt, pt, 0, \
                                                                       self.edits[QadDynamicInputEditEnum.EDIT_REL_ANG_NEXT_PT], True) # LineMarker arc only
                  self.edits[QadDynamicInputEditEnum.EDIT_REL_ANG_NEXT_PT].move(editPt.x(), editPt.y())
                  del editPt
                  # I draw the marker line
                  self.edits[QadDynamicInputEditEnum.EDIT_REL_ANG_NEXT_PT].setLinesMarker(lineMarkers)
                  del lineMarkers
            elif gType == "ARC": # moving a point of an arc in grip mode
               center = self.nextPart.center

               if self.edits[QadDynamicInputEditEnum.EDIT_DIST_NEXT_PT].isVisible():
                  # used for arc radius length at the starting point of the next part
                  p2 = self.nextPart.getStartPt()
                  editPt, lineMarkers = self.getPosAndLineMarkerForLine(center, p2, \
                                                                        0, self.edits[QadDynamicInputEditEnum.EDIT_DIST_NEXT_PT])
                  self.edits[QadDynamicInputEditEnum.EDIT_DIST_NEXT_PT].move(editPt.x(), editPt.y())
                  del editPt
                  # I draw the marker line
                  self.edits[QadDynamicInputEditEnum.EDIT_DIST_NEXT_PT].setLinesMarker(lineMarkers)
                  del lineMarkers

               if self.edits[QadDynamicInputEditEnum.EDIT_REL_DIST_NEXT_PT].isVisible():
                  # used for radius length at the end point of the next part if arc
                  p2 = self.nextPart.getEndPt()
                  editPt, lineMarkers = self.getPosAndLineMarkerForLine(center, p2, \
                                                                        0, self.edits[QadDynamicInputEditEnum.EDIT_REL_DIST_NEXT_PT])
                  self.edits[QadDynamicInputEditEnum.EDIT_REL_DIST_NEXT_PT].move(editPt.x(), editPt.y())
                  del editPt
                  # I draw the marker line
                  self.edits[QadDynamicInputEditEnum.EDIT_REL_DIST_NEXT_PT].setLinesMarker(lineMarkers)
                  del lineMarkers

      else:
         if self.edits[QadDynamicInputEditEnum.PROMPT_EDIT].isVisible():
            x, y = self.adjustEditPosition(x, y, width, height)

      if self.edits[QadDynamicInputEditEnum.PROMPT_EDIT].isVisible():
         self.edits[QadDynamicInputEditEnum.PROMPT_EDIT].move(x, y)


   # ============================================================================
   # refreshResult
   # ============================================================================
   def refreshResult(self, mousePos = None):
      # calculates the result and returns True if the operation is successful
      # depending on the context it can be a point -> self.resPt or a value (number, string, bool...) -> self.resValue
      # the result is also set to string format in self.resStr
      self.resValue = None
      self.resStr = ""

      # if the result can be a point
      if self.inputType & QadInputTypeEnum.POINT2D or self.inputType & QadInputTypeEnum.POINT3D:
         if mousePos is not None:
            point = self.canvas.getCoordinateTransform().toMapCoordinates(mousePos) # posizione
         else:
            point = self.canvas.getCoordinateTransform().toMapCoordinates(self.canvas.mouseLastXY()) # posizione

         # if the coordinate widgets are visible you are looking for a point
         if self.edits[QadDynamicInputEditEnum.EDIT_X].isVisible():
            # you are looking for a point through explicit coordinates (relative to the previous point or absolute)

            if self.prevPoint is None: # if it is not set in the dynamic input I look for it in the plugin
               if self.plugIn.lastPoint is None:
                  prevPt = QgsPointXY(0,0)
               else:
                  prevPt = self.plugIn.lastPoint
            else:
               prevPt = self.prevPoint

            # if they are relative coordinates
            relative = True if self.dynPiCoords == 0 else False
            # if they are polar coordinates
            polar = True if self.dynPiFormat == 0 else False
            if self.edits[QadDynamicInputEditEnum.EDIT_SYMBOL_COORD_TYPE].isVisible():
               coordType = self.edits[QadDynamicInputEditEnum.EDIT_SYMBOL_COORD_TYPE].toPlainText()
               if "@" in coordType: relative = True
               elif "#" in coordType: relative = False
               polar = True if "<" in coordType else False
            else: # if it is not explicit that it is relative but it is because of dynPiCoords
               prevPt = self.prevPoint # if there is no previous point set in the dynamic input
               if prevPt is None:
                  relative = False
                  polar = False

            if polar == False: # coordinate cartesiane
               # x
               if self.edits[QadDynamicInputEditEnum.EDIT_X].isLockedValue() == False:
                  self.resPt.setX(point.x())
               else:
                  value = self.edits[QadDynamicInputEditEnum.EDIT_X].checkValid() # returns the value if valid
                  if value is None:
                     self.resPt.setX(point.x())
                  else:
                     if relative:
                        value = prevPt.x() + value
                     self.resPt.setX(value)

               # y
               if self.edits[QadDynamicInputEditEnum.EDIT_Y].isLockedValue() == False:
                  self.resPt.setY(point.y())
               else:
                  value = self.edits[QadDynamicInputEditEnum.EDIT_Y].checkValid() # returns the value if valid
                  if value is None:
                     self.resPt.setY(point.y())
                  else:
                     if relative:
                        value = prevPt.y() + value
                     self.resPt.setY(value)

               if self.edits[QadDynamicInputEditEnum.EDIT_Z].isVisible():
                  # z
                  if self.edits[QadDynamicInputEditEnum.EDIT_Z].isLockedValue() == False:
                     self.resPt.setZ(point.z())
                  else:
                     value = self.edits[QadDynamicInputEditEnum.EDIT_Z].checkValid() # returns the value if valid
                     if value is None:
                        self.resPt.setZ(point.z())
                     else:
                        self.resPt.setZ(prevPt.z() + value if relative else value)
            elif prevPt is not None: # coordinate polari
               # in the case of polar coordinates EDIT_X contains the distance from the previous point or from 0.0
               if self.edits[QadDynamicInputEditEnum.EDIT_X].isLockedValue():
                  dist = self.edits[QadDynamicInputEditEnum.EDIT_X].checkValid() # returns the value if valid
                  if dist is None:
                     if relative:
                        dist = qad_utils.getDistance(prevPt, point)
                     else:
                        dist = qad_utils.getDistance(QgsPointXY(0, 0), point)
               else:
                  if relative:
                     dist = qad_utils.getDistance(prevPt, point)
                  else:
                     dist = qad_utils.getDistance(QgsPointXY(0, 0), point)

               # in the case of polar coordinates EDIT_Y contains the angle
               if self.edits[QadDynamicInputEditEnum.EDIT_Y].isLockedValue():
                  angle = self.edits[QadDynamicInputEditEnum.EDIT_Y].checkValid() # returns the value if valid
                  if angle is None:
                     angle = qad_utils.getAngleBy2Pts(prevPt, point, 0) # without tolerance
               else:
                  angle = qad_utils.getAngleBy2Pts(prevPt, point, 0) # without tolerance

               if relative:
                  pt = qad_utils.getPolarPointByPtAngle(prevPt, angle, dist)
               else:
                  pt = qad_utils.getPolarPointByPtAngle(QgsPointXY(0, 0), angle, dist)

               self.resPt.setX(pt.x())
               self.resPt.setY(pt.y())

            self.resStr = self.resPt.toString()
            return True

         if self.isDimensionalWidgetVisib():
            if self.prevPoint is not None: # involves inserting a new point at the end of the line
               # you are looking for a point through the distance and angle from the previous point
               if self.edits[QadDynamicInputEditEnum.EDIT_DIST_PREV_PT].isLockedValue() == False:
                  dist = qad_utils.getDistance(self.prevPoint, point)
               else:
                  dist = self.edits[QadDynamicInputEditEnum.EDIT_DIST_PREV_PT].checkValid() # returns the value if valid
                  if dist is None: dist = qad_utils.getDistance(self.prevPoint, point)

               if self.edits[QadDynamicInputEditEnum.EDIT_ANG_PREV_PT].isLockedValue() == False:
                  angle = qad_utils.getAngleBy2Pts(self.prevPoint, point, 0) # without tolerance
               else:
                  angle = self.edits[QadDynamicInputEditEnum.EDIT_ANG_PREV_PT].checkValid() # returns the value in radians if valid
                  if angle is None:
                     angle = qad_utils.getAngleBy2Pts(self.prevPoint, point, 0) # without tolerance
                  else:
                     angleMouse = qad_utils.getAngleBy2Pts(self.prevPoint, point, 0) # without tolerance
                     # if the mouse forms an angle between 180 and 360 then the angle entered must be subtracted from 360 degrees
                     if angleMouse >= math.pi and angleMouse < 2 * math.pi:
                        angle = (2 * math.pi) - angle

               pt = qad_utils.getPolarPointByPtAngle(self.prevPoint, angle, dist)
               self.resPt.setX(pt.x())
               self.resPt.setY(pt.y())
               self.resStr = self.resPt.toString()
               return True
            else: # moving a point in grip mode
               # if the "distance from previous point" dimensions widget is visible
               if self.edits[QadDynamicInputEditEnum.EDIT_DIST_PREV_PT].isVisible() and \
                  self.edits[QadDynamicInputEditEnum.EDIT_DIST_PREV_PT].isLockedValue() and \
                  self.prevPart is not None and self.prevPart.whatIs() == "LINE":
                  dist = self.edits[QadDynamicInputEditEnum.EDIT_DIST_PREV_PT].checkValid() # returns the value if valid
                  if dist is not None:
                     pt1 = self.prevPart.getStartPt()
                     pt2 = self.prevPart.getEndPt()
                     angle = qad_utils.getAngleBy2Pts(pt1, pt2, 0) # without tolerance
                     pt = qad_utils.getPolarPointByPtAngle(pt1, angle, dist)
                     self.resPt.setX(pt.x())
                     self.resPt.setY(pt.y())
                     self.resStr = self.resPt.toString()
                     return True

               # if the dimensions widget in grip mode "distance to next point" is visible
               elif self.edits[QadDynamicInputEditEnum.EDIT_DIST_NEXT_PT].isVisible() and \
                    self.edits[QadDynamicInputEditEnum.EDIT_DIST_NEXT_PT].isLockedValue() and \
                    self.nextPart is not None and self.nextPart.whatIs() == "LINE":
                  dist = self.edits[QadDynamicInputEditEnum.EDIT_DIST_NEXT_PT].checkValid() # returns the value if valid
                  if dist is not None:
                     pt1 = self.nextPart.getEndPt()
                     pt2 = self.nextPart.getStartPt()
                     angle = qad_utils.getAngleBy2Pts(pt1, pt2, 0) # without tolerance
                     pt = qad_utils.getPolarPointByPtAngle(pt1, angle, dist)
                     self.resPt.setX(pt.x())
                     self.resPt.setY(pt.y())
                     self.resStr = self.resPt.toString()
                     return True

               # if the "angle from previous point" dimensions widget is visible
               elif self.edits[QadDynamicInputEditEnum.EDIT_ANG_PREV_PT].isVisible() and \
                    self.edits[QadDynamicInputEditEnum.EDIT_ANG_PREV_PT].isLockedValue() and \
                    self.prevPart is not None and self.prevPart.whatIs() == "LINE":
                  angle = self.edits[QadDynamicInputEditEnum.EDIT_ANG_PREV_PT].checkValid() # returns the value in radians if valid
                  if angle is not None:
                     pt1 = self.prevPart.getStartPt()
                     angleMouse = qad_utils.getAngleBy2Pts(pt1, point, 0) # without tolerance
                     # if the mouse forms an angle between 180 and 360 then the angle entered must be subtracted from 360 degrees
                     if angleMouse >= math.pi and angleMouse < 2 * math.pi:
                        angle = (2 * math.pi) - angle
                     pt = qad_utils.getPolarPointByPtAngle(pt1, angle, self.prevPart.length())
                     self.resPt.setX(pt.x())
                     self.resPt.setY(pt.y())
                     self.resStr = self.resPt.toString()
                     return True

               # if the "angle from next point" dimensions widget is visible
               elif self.edits[QadDynamicInputEditEnum.EDIT_ANG_NEXT_PT].isVisible() and \
                    self.edits[QadDynamicInputEditEnum.EDIT_ANG_NEXT_PT].isLockedValue() and \
                    self.nextPart is not None and self.nextPart.whatIs() == "LINE":
                  angle = self.edits[QadDynamicInputEditEnum.EDIT_ANG_NEXT_PT].checkValid() # returns the value in radians if valid
                  if angle is not None:
                     pt1 = self.nextPart.getEndPt()
                     angleMouse = qad_utils.getAngleBy2Pts(pt1, point, 0) # without tolerance
                     # if the mouse forms an angle between 180 and 360 then the angle entered must be subtracted from 360 degrees
                     if angleMouse >= math.pi and angleMouse < 2 * math.pi:
                        angle = (2 * math.pi) - angle
                     pt = qad_utils.getPolarPointByPtAngle(pt1, angle, self.nextPart.length())
                     self.resPt.setX(pt.x())
                     self.resPt.setY(pt.y())
                     self.resStr = self.resPt.toString()
                     return True

               # if the dimensions widget in grip mode "distance from the previous position of the same point in the direction from the previous point" is visible
               elif self.edits[QadDynamicInputEditEnum.EDIT_REL_DIST_PREV_PT].isVisible() and \
                    self.edits[QadDynamicInputEditEnum.EDIT_REL_DIST_PREV_PT].isLockedValue() and \
                    self.prevPart is not None and self.prevPart.whatIs() == "LINE":
                  dist = self.edits[QadDynamicInputEditEnum.EDIT_REL_DIST_PREV_PT].checkValid() # returns the value if valid
                  if dist is not None:
                     pt1 = self.prevPart.getStartPt()
                     pt2 = self.prevPart.getEndPt()
                     angle = qad_utils.getAngleBy2Pts(pt1, pt2, 0) # without tolerance
                     pt = qad_utils.getPolarPointByPtAngle(pt2, angle, dist)
                     self.resPt.setX(pt.x())
                     self.resPt.setY(pt.y())
                     self.resStr = self.resPt.toString()
                     return True

               # if the dimensions widget in grip mode "distance from the previous position of the same point in the direction from the next point" is visible
               elif self.edits[QadDynamicInputEditEnum.EDIT_REL_DIST_NEXT_PT].isVisible() and \
                    self.edits[QadDynamicInputEditEnum.EDIT_REL_DIST_NEXT_PT].isLockedValue() and \
                    self.nextPart is not None and self.nextPart.whatIs() == "LINE":
                  dist = self.edits[QadDynamicInputEditEnum.EDIT_REL_DIST_NEXT_PT].checkValid() # returns the value if valid
                  if dist is not None:
                     pt1 = self.nextPart.getEndPt()
                     pt2 = self.nextPart.getStartPt()
                     angle = qad_utils.getAngleBy2Pts(pt1, pt2, 0) # without tolerance
                     pt = qad_utils.getPolarPointByPtAngle(pt2, angle, dist)
                     self.resPt.setX(pt.x())
                     self.resPt.setY(pt.y())
                     self.resStr = self.resPt.toString()
                     return True

               # if the dimensions widget in grip mode "angle relative to angle from previous point" is visible
               elif self.edits[QadDynamicInputEditEnum.EDIT_REL_ANG_PREV_PT].isVisible() and \
                    self.edits[QadDynamicInputEditEnum.EDIT_REL_ANG_PREV_PT].isLockedValue() and \
                    self.prevPart is not None and self.prevPart.whatIs() == "LINE":
                  angle = self.edits[QadDynamicInputEditEnum.EDIT_REL_ANG_PREV_PT].checkValid() # returns the value in radians if valid
                  if angle is not None:
                     pt1 = self.prevPart.getStartPt()
                     pt2 = self.prevPart.getEndPt()
                     anglePart = qad_utils.getAngleBy2Pts(pt1, pt2, 0) # without tolerance
                     angleMouse = qad_utils.getAngleBy2Pts(pt1, point, 0) # without tolerance
                     diffAngle = qad_utils.normalizeAngle(angleMouse - anglePart)
                     # if the mouse forms an angle between 180 and 360 then the angle entered must be subtracted from 360 degrees
                     if diffAngle >= math.pi and diffAngle < (2 * math.pi):
                        pt = qad_utils.getPolarPointByPtAngle(pt1, anglePart-angle, self.prevPart.length())
                     else:
                        pt = qad_utils.getPolarPointByPtAngle(pt1, anglePart+angle, self.prevPart.length())
                     self.resPt.setX(pt.x())
                     self.resPt.setY(pt.y())
                     self.resStr = self.resPt.toString()
                     return True

               # if the dimensions widget in grip mode "distance from previous point" is visible
               elif self.edits[QadDynamicInputEditEnum.EDIT_REL_ANG_NEXT_PT].isVisible() and \
                  self.edits[QadDynamicInputEditEnum.EDIT_REL_ANG_NEXT_PT].isLockedValue() and \
                    self.nextPart is not None and self.nextPart.whatIs() == "LINE":
                  angle = self.edits[QadDynamicInputEditEnum.EDIT_REL_ANG_NEXT_PT].checkValid() # returns the value in radians if valid
                  if angle is not None:
                     pt1 = self.nextPart.getEndPt()
                     pt2 = self.nextPart.getStartPt()
                     anglePart = qad_utils.getAngleBy2Pts(pt1, pt2, 0) # without tolerance
                     angleMouse = qad_utils.getAngleBy2Pts(pt1, point, 0) # without tolerance
                     diffAngle = qad_utils.normalizeAngle(angleMouse - anglePart)
                     # if the mouse forms an angle between 180 and 360 then the angle entered must be subtracted from 360 degrees
                     if diffAngle >= math.pi and diffAngle < (2 * math.pi):
                        pt = qad_utils.getPolarPointByPtAngle(pt1, anglePart-angle, self.nextPart.length())
                     else:
                        pt = qad_utils.getPolarPointByPtAngle(pt1, anglePart+angle, self.nextPart.length())
                     self.resPt.setX(pt.x())
                     self.resPt.setY(pt.y())
                     self.resStr = self.resPt.toString()
                     return True

               else: # if no value was unblocked
                  self.resPt.setX(point.x())
                  self.resPt.setY(point.y())
                  self.resStr = self.resPt.toString()
                  return True

         # you are looking for an angle through the previous point
         if self.inputType & QadInputTypeEnum.ANGLE and self.prevPoint is not None:
            if self.edits[QadDynamicInputEditEnum.EDIT].isLockedValue() == False:
               self.resPt.setX(point.x())
               self.resPt.setY(point.y())
               self.resStr = self.resPt.toString()
               self.resValue = qad_utils.getAngleBy2Pts(self.prevPoint, self.resPt, 0) # without tolerance
               return True
            else:
               dist = qad_utils.getDistance(self.prevPoint, point)
               angle = self.edits[QadDynamicInputEditEnum.EDIT].checkValid() # returns the value in radians if valid
               if angle is not None:
                  pt = qad_utils.getPolarPointByPtAngle(self.prevPoint, angle, dist)
                  self.resPt.setX(pt.x())
                  self.resPt.setY(pt.y())
                  self.resStr = self.resPt.toString()
                  return True

         # you are looking for a float value through the previous point
         if self.inputType & QadInputTypeEnum.FLOAT and self.prevPoint is not None:
            if self.edits[QadDynamicInputEditEnum.EDIT].isLockedValue() == False:
               self.resPt.setX(point.x())
               self.resPt.setY(point.y())
               self.resStr = self.resPt.toString()
               self.resValue = qad_utils.getDistance(self.prevPoint, self.resPt)
               return True
            else:
               angle = qad_utils.getAngleBy2Pts(self.prevPoint, point, 0) # without tolerance
               dist = self.edits[QadDynamicInputEditEnum.EDIT].checkValid() # returns the value if valid
               if dist is not None:
                  pt = qad_utils.getPolarPointByPtAngle(self.prevPoint, angle, dist)
                  self.resPt.setX(pt.x())
                  self.resPt.setY(pt.y())
                  self.resStr = self.resPt.toString()
                  return True

            return True


      if self.inputType & QadInputTypeEnum.STRING or self.inputType & QadInputTypeEnum.INT or \
         self.inputType & QadInputTypeEnum.LONG or self.inputType & QadInputTypeEnum.FLOAT or \
         self.inputType & QadInputTypeEnum.BOOL or self.inputType & QadInputTypeEnum.ANGLE:
         if self.edits[QadDynamicInputEditEnum.EDIT].isVisible():
            if self.edits[QadDynamicInputEditEnum.EDIT].isLockedValue() == True:
               self.resValue = self.edits[QadDynamicInputEditEnum.EDIT].checkValid() # returns the value if valid
               if self.resValue is None:
                  self.resStr = ""
                  return False
               else:
                  if self.inputType & QadInputTypeEnum.ANGLE:
                     self.resStr = unicode(qad_utils.toDegrees(self.resValue))
                  else:
                     self.resStr = unicode(self.resValue)
                  return True
            elif self.inputType & QadInputTypeEnum.ANGLE and self.prevPoint is not None:
               self.resValue = qad_utils.getAngleBy2Pts(self.prevPoint, self.resPt, 0) # without tolerance
               self.resStr = unicode(qad_utils.toDegrees(self.resValue))
               return True
         else:
            self.resValue = None
            self.resStr = ""

      return False


   # ============================================================================
   # keyPressEvent
   # ============================================================================
   def keyPressEvent(self, e):
      if self.currentEdit is None:
         return
      if e.key() == Qt.Key_Comma: # ","
         # if the result can be a point
         if self.inputType & QadInputTypeEnum.POINT2D or self.inputType & QadInputTypeEnum.POINT2D:
            self.forcedCoordWidgetVisib = True # editaz forzata delle coordinate
            if self.currentEdit != QadDynamicInputEditEnum.EDIT_X and \
               self.currentEdit != QadDynamicInputEditEnum.EDIT_Y and \
               self.currentEdit != QadDynamicInputEditEnum.EDIT_Z:
               coord = self.edits[self.currentEdit].toPlainText()
               self.currentEdit = QadDynamicInputEditEnum.EDIT_X
               self.edits[QadDynamicInputEditEnum.EDIT_X].setLockedValue(True) # if it is possible change the lock status
               self.edits[QadDynamicInputEditEnum.EDIT_X].showMsg(coord)
            self.show(True)
            self.setNextCurrentEdit()
         else:
            QTextEdit.keyPressEvent(self.edits[self.currentEdit], e)
            #self.edits[self.currentEdit].keyPressEvent(e)

      elif e.text() == "@" or e.text() == "#" or e.text() == "<":
         # if the result can be a point
         if self.inputType & QadInputTypeEnum.POINT2D or self.inputType & QadInputTypeEnum.POINT2D:
            self.forcedCoordWidgetVisib = True # editaz forzata delle coordinate
            value = self.edits[QadDynamicInputEditEnum.EDIT_SYMBOL_COORD_TYPE].toPlainText()
            alreadyPolar = True if value.find("<") >= 0 else False
            if e.text() == "@" or e.text() == "#":
               value = e.text()
               if alreadyPolar: value = value + "<"
            else: # "<"
               if value.find("@") >= 0: value = "@"
               elif value.find("#") >= 0: value = "#"
               if alreadyPolar == False: value = value + "<"

            self.edits[QadDynamicInputEditEnum.EDIT_SYMBOL_COORD_TYPE].showMsg(value)
            if self.currentEdit != QadDynamicInputEditEnum.EDIT_X and \
               self.currentEdit != QadDynamicInputEditEnum.EDIT_Y and \
               self.currentEdit != QadDynamicInputEditEnum.EDIT_Z:
               coord = self.edits[self.currentEdit].toPlainText()
               self.currentEdit = QadDynamicInputEditEnum.EDIT_X
               self.edits[QadDynamicInputEditEnum.EDIT_X].showMsg(coord)
            self.show(True)

      elif e.key() == Qt.Key_Return or e.key == Qt.Key_Enter:
         self.submitCurrentInput()
      else:
         self.edits[self.currentEdit].keyPressEvent(e)


   # ============================================================================
   # submitCurrentInput
   # ============================================================================
   def submitCurrentInput(self):
      """Evaluate dynamic input using the same semantics as pressing Enter."""
      # if there is no value locked widget
      if self.anyLockedValueEdit() == False:
         msg = ""
         # if @ or # was pressed
         if self.edits[QadDynamicInputEditEnum.EDIT_SYMBOL_COORD_TYPE].isVisible():
            coordType = self.edits[QadDynamicInputEditEnum.EDIT_SYMBOL_COORD_TYPE].toPlainText()
            if "@" in coordType: msg = "@"
            elif "#" in coordType: msg = "#"
         self.showEvaluateMsg(msg)
         return True

      if self.currentEdit is not None:
         currentWidget = self.edits[self.currentEdit]
         # if the widget content has been modified by the user
         if currentWidget.isLockedValue() == True:
            value = currentWidget.toPlainText()
            # check if it is an option of the active command
            keyWord = self.evaluateKeyWords(value)
            if keyWord is not None:
               self.showEvaluateMsg(keyWord)
               return True
            # otherwise if a point was expected and it is an osnap option
            elif (self.inputType & QadInputTypeEnum.POINT2D or self.inputType & QadInputTypeEnum.POINT3D) and \
                  str2snapTypeEnum(value) != -1:
               currentWidget.showMsg("")
               currentWidget.setLockedValue(False)
               self.showEvaluateMsg(value)
               return True
            # otherwise if a point was expected and it is the M2P option "midpoint between 2 points"
            elif (self.inputType & QadInputTypeEnum.POINT2D or self.inputType & QadInputTypeEnum.POINT3D) and \
                  (value.upper() == QadMsg.translate("Snap", "M2P") or value.upper() == "_M2P"):
               currentWidget.showMsg("")
               currentWidget.setLockedValue(False)
               self.showEvaluateMsg(value)
               return True
            # otherwise check the validity of the value
            elif currentWidget.checkValid() is not None:
               msg = self.resStr if self.refreshResult() == True else "" # I recalculate the result and use it in string format
               self.showEvaluateMsg(msg)
               return True
         return False

      msg = self.resStr if self.refreshResult() == True else "" # I recalculate the result and use it in string format
      self.showEvaluateMsg(msg)
      return True


   # ============================================================================
   # evaluateKeyWords
   # ============================================================================
   def evaluateKeyWords(self, cmd):
      # The required portion of the keyword is specified in uppercase characters,
      # and the remainder of the keyword is specified in lowercase characters.
      # The uppercase abbreviation can be anywhere in the keyword
      if cmd[0] == "_": # versione inglese
         keyWord, Msg = qad_utils.evaluateCmdKeyWords(cmd[1:], self.englishKeyWords)
         if keyWord is None: return None
         # I searc for the corresponding keyword in the local language
         i = 0
         for k in self.englishKeyWords:
            if k == keyWord:
               return self.keyWords[i]
            i = i + 1
         return None
      else:
         keyWord, Msg = qad_utils.evaluateCmdKeyWords(cmd, self.keyWords)
         return keyWord
