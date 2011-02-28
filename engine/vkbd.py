# vim:set et sts=4 sw=4:
# -*- coding: utf-8 -*-
#
# ibus-skk - The SKK engine for IBus
#
# Copyright (C) 2011 Daiki Ueno <ueno@unixuser.org>
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA
# 02110-1301, USA.

from ibus import keysyms
from ibus import modifier
import eekboard, virtkey
import skk

KEYBOARD_MODE_NONE, KEYBOARD_MODE_US, KEYBOARD_MODE_KANA = range(3)

class Vkbd(object):
    def __init__(self, engine, path):
        self.__engine = engine
        self.__keyboard_mode = KEYBOARD_MODE_NONE
        self.__keyboard = eekboard.XmlKeyboard(path,
                                               eekboard.MODIFIER_BEHAVIOR_LATCH)
        self.__keyboard.connect('key-pressed', self.__key_pressed_cb)
        self.__keyboard.connect('key-released', self.__key_released_cb)
        self.__virtkey = virtkey.virtkey()
        self.__eekboard = eekboard.Eekboard()
        self.__context = self.__eekboard.create_context("")
        self.__context.set_keyboard(self.__keyboard)

    keyboard_mode = property(lambda self: self.__keyboard_mode)

    def update_input_mode(self):
        if self.__keyboard_mode == KEYBOARD_MODE_KANA:
            if self.__engine.input_mode == skk.INPUT_MODE_KATAKANA:
                self.__context.set_group(1)
            else:
                self.__context.set_group(2)

    def enable(self):
        self.__eekboard.push_context(self.__context)

    def disable(self):
        self.__eekboard.pop_context()

    def activate_keyboard_mode(self, keyboard_mode, input_mode):
        if self.__keyboard_mode == keyboard_mode:
            return
        self.__keyboard_mode = keyboard_mode
        if self.__keyboard_mode == KEYBOARD_MODE_NONE:
            self.__context.hide_keyboard()
        elif self.__keyboard_mode == KEYBOARD_MODE_US:
            self.__context.set_group(0)
            self.__context.show_keyboard()
        elif self.__keyboard_mode == KEYBOARD_MODE_KANA:
            if input_mode == skk.INPUT_MODE_KATAKANA:
                self.__context.set_group(1)
            else:
                self.__context.set_group(2)
                self.__context.show_keyboard()

    def __process_key_event(self, key, modifiers):
        symbol = key.get_symbol()
        if symbol.is_modifier() or not isinstance(symbol, eekboard.Keysym):
            return False

        # handle special keys
        if symbol.get_xkeysym() == keysyms.Eisu_toggle:
            if modifiers & modifier.RELEASE_MASK:
                self.activate_keyboard_mode(KEYBOARD_MODE_US,
                                            self.__engine.input_mode)
            return True

        if symbol.get_xkeysym() == keysyms.Hiragana_Katakana:
            if modifiers & modifier.RELEASE_MASK:
                self.activate_keyboard_mode(KEYBOARD_MODE_KANA,
                                            self.__engine.input_mode)
            return True

        # let the engine handle the key event
        modifiers |= self.__keyboard.get_modifiers()
        if self.__engine.process_key_event(symbol.get_xkeysym(), \
                                               key.get_keycode(), \
                                               modifiers):
            return True

        # if the event is not handled, pass it back with virtkey
        if modifiers & modifier.RELEASE_MASK:
            self.__virtkey.release_keycode(key.get_keycode())
        else:
            self.__virtkey.press_keycode(key.get_keycode())

    def __key_pressed_cb(self, keyboard, key):
        return self.__process_key_event(key, 0)

    def __key_released_cb(self, keyboard, key):
        return self.__process_key_event(key, modifier.RELEASE_MASK)
