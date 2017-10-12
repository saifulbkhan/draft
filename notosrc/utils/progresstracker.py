# This file is a rewrite of gtkprogresstracker.c from the Gtk library but
# is not available through PyGObject 3.24, which is why this module exists.
# The following copyright, therefore, has been pasted from the ogirinal file:
#
# Copyright © 2016 Endless Mobile Inc.
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library. If not, see <http://www.gnu.org/licenses/>.
#
# Authors: Matthew Watson <mattdangerw@gmail.com>

import math
from enum import Enum

gtk_slowdown = 1.0

class ProgressState(Enum):
    BEFORE = 0
    DURING = 1
    AFTER = 2

class ProgressTracker(object):
    """
    Tracks progress through GTK animations

    Progress tracker is small helper for tracking progress through gtk
    animations. It's a simple zero-initable struct, meant to be thrown in a
    widget's private data without the need for setup or teardown.

    Progress tracker will handle translating frame clock timestamps to a
    fractional progress value for interpolating between animation targets.

    Progress tracker will use the GTK_SLOWDOWN environment variable to control
    the speed of animations. This can be useful for debugging.
    """
    self.is_running = False
    self.last_frame_time = 0
    self.duration = 0
    self.iteration = 0.0
    self.iteration_count = 0.0

    def start(self, duration, delay, iteration_count):
        """
        Begins tracking progress for a new animation. Clears all previous state.

        :param self: The progress tracker
        :param duration: integer -- Animation duration in microseconds
        :param delay: Animation integer -- delay in microseconds
        :param iteration_count: double -- Number of iterations to run the animation, must be >= 0
        """
        self.is_running = True
        self.last_frame_time = 0
        self.duration = duration
        self.iteration = (0 - delay) / duration
        self.iteration_count = iteration_count

    def finish(self):
        """
        Stops running the current animation

        :param self: The progress tracker
        """
        self.is_running = False

    def advance_frame(self, frame_time):
        """
        Increments the progress of the animation forward a frame. If no
        animation has been started, does nothing.

        :param self: The progress tracker
        :param frame_time: integer -- The current frame time, usually from the frame clock.
        """
        if not self.is_running:
            return

        if self.last_frame_time == 0:
            self.last_frame_time = frame_time
            return

        if frame_time < self.last_frame_time:
            # TODO: Warn: progress tracker frame set backwards, ignoring.
            return

        delta = (frame_time - self.last_frame_time) / gtk_slowdown / self.duration
        self.last_frame_time = frame_time
        self.iteration += delta

    def skip_frame(self, frame_time):
        """
        Does not update the progress of the animation forward, but records the
        frame to calculate future deltas. Calling this each frame will
        effectively pause the animation.

        :param self: The progress tracker
        :param frame_time: integer -- The current frame time, usually from the frame clock.
        """
        if not self.is_running:
            return

        self.last_frame_time = frame_time

    def get_state(self):
        """
        Returns whether the tracker is before, during or after the currently
        started animation. The tracker will only ever be in the before state if
        the animation was started with a delay. If no animation has been
        started, returns ProgressState.AFTER.

        :param self: The progress tracker
        :returns: ProgressState
        """
        if not self.is_running or self.iteration > self.iteration_count:
            return ProgressState.AFTER
        if self.iteration < 0:
            return ProgressState.BEFORE
        return ProgressState.DURING

    def get_iteration(self):
        """
        Returns the fractional number of cycles the animation has completed. For
        example, it you started an animation with iteration-count of 2 and are half
        way through the second animation, this returns 1.5.

        :param self: The progress tracker
        :returns: double -- The current iteration
        """
        if self.is_running:
            return max(min(self.iteration, self.iteration_count), 0.0)
        return 1.0

    def get_iteration_cycle(self):
        """
        Returns an integer index of the current iteration cycle tracker is
        progressing through. Handles edge cases, such as an iteration value of 2.0
        which could be considered the end of the second iteration of the beginning of
        the third, in the same way as gtk_progress_tracker_get_progress().

        :param self: The progress tracker
        :returns: integer -- The count of current animation cycle
        """
        iteration = self.get_iteration():
            return 0

        return math.ceil(iteration) - 1

    def get_progress(self, reversed):
        """
        Gets the progress through the current animation iteration, from [0, 1]. Use
        to interpolate between animation targets. If reverse is true each iteration
        will begin at 1 and end at 0.

        :param self: The progress tracker
        :param reversed: boolean -- If progress should be reversed
        :returns: double -- The progress value
        """
        iteration = self.get_iteration()
        iteration_cycle = self.get_iteration_cycle

        progress = iteration - iteration_cycle
        if reversed:
            return 1.0 - progress
        return progress

    def _ease_out_cubic(self, t):
        """
        From clutter-easing.c, based on Robert Penner's
        infamous easing equations, MIT license.
        """
        p = t - 1
        return p**3 + 1

    def get_ease_out_cubic(self, reversed):
        """
        Applies a simple ease out cubic function to the result of
        gtk_progress_tracker_get_progress().

        :param self: The progress tracker
        :param reversed: boolean -- If progress should be reversed before applying the ease function.
        :returns: double -- The eased progress value
        """
        progress = self.get_progress(reversed)
        return self._ease_out_cubic(progress)
