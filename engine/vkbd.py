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

KEYBOARD_MODE_US, KEYBOARD_MODE_KANA = range(2)
KEYBOARD_TYPE_QWERTY, KEYBOARD_TYPE_TABLE = range(2)

INPUT_MODE_HIRAGANA, \
INPUT_MODE_KATAKANA, \
INPUT_MODE_HALF_WIDTH_KATAKANA, \
INPUT_MODE_LATIN, \
INPUT_MODE_WIDE_LATIN = range(5)

class Vkbd(object):
    def __init__(self, engine, qwerty_path, table_path):
        self.__engine = engine
        self.__input_mode = None

        self.__eekboard = eekboard.Eekboard()
        self.__context = self.__eekboard.create_context("")

        self.__qwerty_keyboard = \
            eekboard.XmlKeyboard(qwerty_path,
                                 eekboard.MODIFIER_BEHAVIOR_LATCH)
        self.__qwerty_keyboard.connect('key-pressed', self.__key_pressed_cb)
        self.__qwerty_keyboard.connect('key-released', self.__key_released_cb)
        self.__qwerty_keyboard_id = \
            self.__context.add_keyboard(self.__qwerty_keyboard)

        self.__table_keyboard = \
            eekboard.XmlKeyboard(table_path,
                                 eekboard.MODIFIER_BEHAVIOR_LATCH)
        self.__table_keyboard.connect('key-pressed', self.__key_pressed_cb)
        self.__table_keyboard.connect('key-released', self.__key_released_cb)
        self.__table_keyboard_id = \
            self.__context.add_keyboard(self.__table_keyboard)

        self.__virtkey = virtkey.virtkey()
        self.__keyboard_mode = None
        self.set_keyboard_type(KEYBOARD_TYPE_QWERTY)
        self.set_keyboard_mode(None)

    keyboard_mode = property(lambda self: self.__keyboard_mode)

    def enable(self):
        self.__eekboard.push_context(self.__context)

    def disable(self):
        self.__eekboard.pop_context()

    def update_input_mode(self, input_mode):
        if self.__input_mode != input_mode:
            self.set_input_mode(input_mode)

    def set_input_mode(self, input_mode):
        self.__input_mode = input_mode
        if self.__keyboard_mode == KEYBOARD_MODE_US:
            self.__context.set_group(0)
        elif self.__keyboard_mode == KEYBOARD_MODE_KANA:
            if self.__input_mode == INPUT_MODE_KATAKANA:
                self.__context.set_group(1)
            elif self.__input_mode == INPUT_MODE_HIRAGANA:
                self.__context.set_group(2)

    def update_keyboard_mode(self, keyboard_mode):
        if self.__keyboard_mode != keyboard_mode:
            self.set_keyboard_mode(keyboard_mode)

    def set_keyboard_mode(self, keyboard_mode):
        self.__keyboard_mode = keyboard_mode
        if self.__keyboard_mode is None:
            self.__context.hide_keyboard()
        else:
            if self.__keyboard_mode == KEYBOARD_MODE_US:
                self.__context.set_group(0)
            else:
                self.__context.set_group(2)
            self.__context.show_keyboard()

    def update_keyboard_type(self, keyboard_type):
        if self.__keyboard_type != keyboard_type:
            self.set_keyboard_type(keyboard_type)

    def set_keyboard_type(self, keyboard_type):
        self.__keyboard_type = keyboard_type
        if self.__keyboard_type == KEYBOARD_TYPE_QWERTY:
            self.__keyboard = self.__qwerty_keyboard
            self.__context.set_keyboard(self.__qwerty_keyboard_id)
        elif self.__keyboard_type == KEYBOARD_TYPE_TABLE:
            self.__keyboard = self.__table_keyboard
            self.__context.set_keyboard(self.__table_keyboard_id)
        self.set_keyboard_mode(self.__keyboard_mode)

    def __process_key_event(self, key, modifiers):
        symbol = key.get_symbol()
        if symbol.is_modifier() or not isinstance(symbol, eekboard.Keysym):
            return False

        keysym = symbol.get_xkeysym()

        # handle special keys
        if keysym == keysyms.Eisu_toggle:
            if modifiers & modifier.RELEASE_MASK:
                self.update_keyboard_mode(KEYBOARD_MODE_US)
            return True

        if keysym == keysyms.Hiragana_Katakana:
            if modifiers & modifier.RELEASE_MASK:
                self.update_keyboard_mode(KEYBOARD_MODE_KANA)
                self.set_input_mode(self.__input_mode)
            return True

        if keysym == keysyms.Num_Lock:
            if modifiers & modifier.RELEASE_MASK:
                if self.__keyboard_type == KEYBOARD_TYPE_QWERTY:
                    keyboard_type = KEYBOARD_TYPE_TABLE
                elif self.__keyboard_type == KEYBOARD_TYPE_TABLE:
                    keyboard_type = KEYBOARD_TYPE_QWERTY
                if self.__keyboard_type != keyboard_type:
                    self.set_keyboard_type(keyboard_type)
            return True

        if keysym == keysyms.Henkan:
            keysym = keysyms.space
            
        # let the engine handle the key event
        modifiers |= self.__keyboard.get_modifiers()
        if self.__engine.process_key_event(keysym, \
                                               key.get_keycode(), \
                                               modifiers):
            return True

        # if the event is not handled, pass it back with virtkey
        if modifiers & modifier.RELEASE_MASK:
            self.__virtkey.release_keysym(symbol.get_xkeysym())
        else:
            self.__virtkey.press_keysym(symbol.get_xkeysym())

    def __key_pressed_cb(self, keyboard, key):
        return self.__process_key_event(key, 0)

    def __key_released_cb(self, keyboard, key):
        return self.__process_key_event(key, modifier.RELEASE_MASK)
