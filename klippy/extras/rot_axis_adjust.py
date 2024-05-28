# Helper script to adjust a axis rotation
# inspired by screw_tilt_adjust.py
#
# This file may be distributed under the terms of the GNU GPLv3 license.
import math
from . import probe

class RotAxisAdjust:
    def __init__(self, config):
        self.config = config
        self.printer = config.get_printer()
        self.screws = []
        self.results = []
        # Read config
        for i in range(99):
            prefix = "pos%d" % (i + 1,)
            if config.get(prefix, None) is None:
                break
            screw_coord = config.getfloatlist(prefix, count=2)
            screw_name = "pos at %.3f,%.3f" % screw_coord
            screw_name = config.get(prefix + "_name", screw_name)
            self.screws.append((screw_coord, screw_name))
        if len(self.screws) != 2:
            raise config.error("rot_axis_adjust: Must have "
                               "at exactly two positions")
        # Initialize ProbePointsHelper
        points = [coord for coord, name in self.screws]
        self.probe_helper = probe.ProbePointsHelper(self.config,
                                                    self.probe_finalize,
                                                    default_points=points)
        self.probe_helper.minimum_points(2)
        # Register command
        self.gcode = self.printer.lookup_object('gcode')
        self.gcode.register_command("ROT_AXIS_ADJUST",
                                    self.cmd_ROT_AXIS_ADJUST,
                                    desc=self.cmd_ROT_AXIS_ADJUST_help)
    cmd_ROT_AXIS_ADJUST_help = "Tool to help adjust rotary axis alignment"

    def cmd_ROT_AXIS_ADJUST(self, gcmd):
        stepper_enable = self.printer.lookup_object('stepper_enable')
        a_enabled = stepper_enable.lookup_enable('stepper_a').is_motor_enabled()
        if not a_enabled:
            self.gcode.respond_info("A axis stepper must be enabled! Not running adjustment")
            return
        self.probe_helper.start_probe(gcmd)

    def get_status(self, eventtime):
        return {
            'results': self.results}

    def probe_finalize(self, offsets, positions):
        self.results = {}
        # Process the read Z values
        for i, screw in enumerate(self.screws):
            coord, name = screw
            z = positions[i][2]
            self.gcode.respond_info(
                "%s : x=%.1f, y=%.1f, z=%.5f" %
                (name, coord[0], coord[1], z))
            self.results["screw%d" % (i + 1,)] = {'z': z}
        y_diff = positions[0][1] - positions[1][1]
        z_diff = positions[0][2] - positions[1][2]
        a_correction = math.atan2(z_diff, y_diff) / (math.pi / 180.0)
        if a_correction > 90.0:
            a_correction = a_correction - 180.0
        elif a_correction < -90.0:
            a_correction = 180 + a_correction
        self.gcode.respond_info("a_correction: %.3f deg" % a_correction)

        if abs(a_correction) > 3.0:
            self.gcode.respond_info("a_coorection too large, not moving axis!")
            return

        toolhead = self.printer.lookup_object('toolhead')
        pos = toolhead.get_position()
        self.gcode.respond_info("a-axis before: %.3f" % pos[3])
        pos[3] += -a_correction
        self.gcode.respond_info("a-axis after: %.3f" % pos[3])
        toolhead.manual_move(pos, 5.0)
        self.gcode.run_script_from_command("G92 A0")

def load_config(config):
    return RotAxisAdjust(config)
