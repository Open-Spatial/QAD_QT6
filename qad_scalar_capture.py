# -*- coding: utf-8 -*-
"""Scalar input capture contracts for external QAD integrations."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .cmd.qad_generic_cmd import QadCommandClass
from .qad_textwindow import QadInputModeEnum, QadInputTypeEnum


@dataclass(frozen=True)
class QadScalarCaptureResult:
   input_type: str
   status: str
   value: Any = None
   message: str = ""


class QadScalarCaptureCommand(QadCommandClass):
   def __init__(self, plugIn, *, prompt, input_type, default, keywords, input_mode, allow_null):
      QadCommandClass.__init__(self, plugIn)
      self.prompt = prompt
      self.inputTypeName = input_type
      self.defaultValue = default
      self.keywords = keywords
      self.inputMode = input_mode
      self.allowNull = allow_null
      self.capturedValue = None
      self.captureError = ""

   def getName(self):
      return "MUNSYSQ_SCALAR"

   def getEnglishName(self):
      return "MUNSYSQ_SCALAR"

   def run(self, msgMapTool = False, msg = None):
      if self.step == 0:
         input_type = {
            "string": QadInputTypeEnum.STRING,
            "integer": QadInputTypeEnum.INT,
            "float": QadInputTypeEnum.FLOAT,
            "keyword": QadInputTypeEnum.KEYWORDS,
            "point": QadInputTypeEnum.POINT2D,
            "point_or_keyword": QadInputTypeEnum.POINT2D | QadInputTypeEnum.KEYWORDS,
            "point_or_distance": QadInputTypeEnum.POINT2D | QadInputTypeEnum.FLOAT,
            "point_or_angle_or_keyword": QadInputTypeEnum.POINT2D | QadInputTypeEnum.ANGLE | QadInputTypeEnum.KEYWORDS,
         }[self.inputTypeName]
         self.waitFor(
            self.prompt,
            input_type,
            self.defaultValue,
            self.keywords,
            self.inputMode,
         )
         self.step = 1
         return False

      # Point input arrives from the QAD map tool when the user clicks the
      # canvas.  The command manager calls run(True) without passing that
      # point as ``msg``; reading only ``msg`` therefore turned every map
      # click into a null value and caused the scalar result to be reported
      # as cancelled.
      point_input_types = (
         "point",
         "point_or_keyword",
         "point_or_distance",
         "point_or_angle_or_keyword",
      )
      if msgMapTool and self.inputTypeName in point_input_types:
         point_map_tool = self.getPointMapTool()
         value = getattr(point_map_tool, "point", None)
      else:
         value = self.defaultValue if msg is None else msg
      try:
         if value is not None:
            if self.inputTypeName == "integer":
               value = int(value)
            elif self.inputTypeName == "float":
               value = float(value)
            elif self.inputTypeName in ("string", "keyword"):
               value = str(value)
      except (TypeError, ValueError):
         self.captureError = "Invalid {0} input.".format(self.inputTypeName)
      self.capturedValue = value
      return True

   def capturedScalarValue(self):
      return self.capturedValue

   def scalarCaptureError(self):
      return self.captureError


def scalar_input_mode(*, allow_null, allow_zero, allow_negative, allow_positive):
   mode = QadInputModeEnum.NONE
   if allow_null == False:
      mode = mode | QadInputModeEnum.NOT_NULL
   if allow_zero == False:
      mode = mode | QadInputModeEnum.NOT_ZERO
   if allow_negative == False:
      mode = mode | QadInputModeEnum.NOT_NEGATIVE
   if allow_positive == False:
      mode = mode | QadInputModeEnum.NOT_POSITIVE
   return mode
