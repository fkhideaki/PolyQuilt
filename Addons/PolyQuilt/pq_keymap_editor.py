# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTIBILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

import os
import bpy
from bpy.types import WorkSpaceTool , Panel
from bpy.utils.toolsystem import ToolDef
from .pq_icon import *
import inspect
import rna_keymap_ui
from bpy.types import AddonPreferences

def draw_tool_keymap( layout ,keyconfing,keymapname ) :
    keymap = keyconfing.keymaps[keymapname]            
    layout.context_pointer_set('keymap', keymap)
    cnt = 0

    for item in reversed(keymap.keymap_items) :
        cnt = max(cnt, (item.oskey, item.shift, item.ctrl, item.alt).count(True))

    for item in reversed(keymap.keymap_items):
        if not (True in (item.oskey, item.shift, item.ctrl, item.alt)):
            continue
        it = layout.row()
        if item.idname != 'mesh.poly_quilt':
            continue

        ic = it.row(align = True)
        ic.ui_units_x = cnt + 2
        ic.prop(item , "active" , text = "" , emboss = True )
        ic.template_event_from_keymap_item(item)

        ic = it.row(align = True)
        ic.prop(item.properties , "tool_mode" , text = "" , emboss = True )

        if( item.properties.tool_mode == 'LOWPOLY' ) :
            im = ic.row()
            im.active = item.properties.is_property_set("geometry_type")
            im.prop(item.properties, "geometry_type" , text = "" , emboss = True , expand = False , icon_only = False )

        if( item.properties.tool_mode == 'BRUSH' ) :
            im = ic.row()
            im.active = item.properties.is_property_set("brush_type")
            im.prop(item.properties, "brush_type" , text = "" , emboss = True , expand = False , icon_only = False )

        if( item.properties.tool_mode == 'LOOPCUT' ) :
            im = ic.row()
            im.active = item.properties.is_property_set("loopcut_mode")
            im.prop(item.properties, "loopcut_mode" , text = "" , emboss = True , expand = False , icon_only = False )

        if (not item.is_user_defined) and item.is_user_modified:
            it.operator("preferences.keyitem_restore", text="", icon='BACK').item_id = item.id
        elif item.is_user_defined :
            it.operator("preferences.keyitem_remove", text="", icon='X').item_id = item.id

    layout.operator(PQ_OT_DirtyKeymap.bl_idname)


def draw_tool_keymap_ui( context , _layout , text , tool) :

    preferences = context.preferences.addons[__package__].preferences

    column = _layout.box().column()    
    row = column.row()
    row.prop( preferences, "keymap_setting_expanded", text="",
        icon='TRIA_DOWN' if preferences.keymap_setting_expanded else 'TRIA_RIGHT')

    row.label(text =text + " Setting")

    if preferences.keymap_setting_expanded :
        keyconfing = context.window_manager.keyconfigs.user
        draw_tool_keymap( column, keyconfing,"3D View Tool: Edit Mesh, " + tool.bl_label )

class PQ_OT_DirtyKeymap(bpy.types.Operator) :
    bl_idname = "addon.polyquilt_dirty_keymap"
    bl_label = "Save Keymap"

    def execute(self, context):
        for keymap in [ k for k in context.window_manager.keyconfigs.user.keymaps if "PolyQuilt" in k.name ] :
            keymap.show_expanded_items = keymap.show_expanded_items
            for item in reversed(keymap.keymap_items) :
                if True in (item.oskey,item.shift,item.ctrl,item.alt) :
                    if item.idname == 'mesh.poly_quilt' :
                        item.active = item.active

        context.preferences.is_dirty = True
#       bpy.ops.wm.save_userpref()
        return {'FINISHED'}

