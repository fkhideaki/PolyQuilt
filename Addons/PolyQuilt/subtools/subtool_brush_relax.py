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

import sys
import bpy
import math
import mathutils
import bmesh
import copy
import bpy_extras
import collections
from ..utils import pqutil
from ..utils import draw_util
from ..QMesh import *
from .subtool import SubToolEx
from ..utils.dpi import *

class SubToolBrushRelax(SubToolEx) :
    name = "RelaxBrushTool"

    def __init__(self, event ,  root) :
        super().__init__(root)
        self.radius = self.preferences.brush_size * dpm()
        self.occlusion_tbl = {}
        self.mirror_tbl = {}
        self.dirty = False
        if self.currentTarget.isEmpty or ( self.currentTarget.isEdge and self.currentTarget.element.is_boundary ) :
            self.effective_boundary = True
        else :
            self.effective_boundary = False

    @staticmethod
    def Check( root , target ) :
        return True

    @classmethod
    def DrawHighlight(cls, gizmo, element):
        def Draw():
            radius = gizmo.preferences.brush_size * dpm()
            strength = gizmo.preferences.brush_strength  
            with draw_util.push_pop_projection2D():
                draw_util.draw_circle2D(
                    gizmo.mouse_pos,
                    radius * strength,
                    color = (1, 0.25, 0.25, 0.25),
                    fill = False,
                    subdivide = 64,
                    dpi = False)
                draw_util.draw_circle2D(
                    gizmo.mouse_pos,
                    radius,
                    color = (1, 1, 1, 0.5),
                    fill = False,
                    subdivide = 64,
                    dpi = False)
        return Draw

    def OnUpdate(self, context, event):
        if event.type == 'MOUSEMOVE':
            self.DoRelax(context, self.mouse_pos)
        elif event.type == self.rootTool.buttonType: 
            if event.value == 'RELEASE':
                if self.dirty:
                    self.bmo.UpdateMesh()
                    return 'FINISHED'
                return 'CANCELLED'
        elif event.value == 'RELEASE':
            self.repeat = False

        return 'RUNNING_MODAL'

    def OnDraw(self, context):
        width = 2.0 if self.effective_boundary else 1.0
        draw_util.draw_circle2D(
            self.mouse_pos,
            self.radius,
            color = (1, 1, 1, 1),
            fill = False,
            subdivide = 64,
            dpi= False,
            width = width)

    def OnDraw3D(self, context):
        pass

    def CollectVerts(self, context, coord):
        rv3d = context.region_data
        region = context.region
        halfW = region.width / 2.0
        halfH = region.height / 2.0
        matrix_world = self.bmo.obj.matrix_world
        matrix = rv3d.perspective_matrix @ matrix_world
        radius = self.radius
        bm = self.bmo.bm
        verts = bm.verts

        select_stack = SelectStack(context, bm)

        select_stack.push()
        select_stack.select_mode(True, False, False)
        bpy.ops.view3d.select_circle(
            x = int(coord.x),
            y = int(coord.y),
            radius = int(radius),
            wait_for_input=False,
            mode='SET')

        occlusion_tbl_get = self.occlusion_tbl.get
        is_target = QSnap.is_target
        new_vec = mathutils.Vector

        coords = []
        cm = {}
        for vt in verts:
            if not vt.select:
                continue
            co = vt.co
            is_occlusion = occlusion_tbl_get(vt)
            if is_occlusion is None:
                is_occlusion = is_target(matrix_world @ co)
                self.occlusion_tbl[vt] = is_occlusion
                if not is_occlusion:
                    continue

            if self.IsFixedVert(vt):
                continue

            pv = matrix @ co.to_4d()
            w = pv.w
            if w < 0.0:
                continue
            px = pv.x * halfW / w + halfW
            py = pv.y * halfH / w + halfH
            p = new_vec((px, py))
            r = (coord - p).length
            if r > radius :
                continue

            x = (radius - r) / radius
            x2 = x ** 2
            cm[vt] = [x2, co.copy()]

        select_stack.pop()

        return cm
    
    def IsFixedVert(self, vt):
        fix_sharp = self.preferences.fix_sharp_edge
        fix_bound = self.preferences.fix_bound_edge
        if fix_sharp or fix_bound:
            for e in vt.link_edges:
                if fix_sharp:
                    if not e.smooth:
                        return True
                if fix_bound:
                    if e.is_boundary:
                        return True
        return False

    def DoRelax(self, context, coord) :
        is_fix_zero = self.preferences.fix_to_x_zero or self.bmo.is_mirror_mode
        coords = self.CollectVerts(context, coord)
        if coords:
            self.dirty = True
        if self.bmo.is_mirror_mode:
            mirrors = {vert : self.bmo.find_mirror(vert) for vert, coord in coords.items()}

        if self.effective_boundary:
            boundary = {c for c in coords.keys() if c.is_boundary}

            result = {}
            for v in boundary:
                if len(v.link_faces) == 1:
                    continue
                le = [e.other_vert(v).co for e in v.link_edges if e.is_boundary]
                result[v] = self.getAvgPos(le)
            for v, co in result.items():
                v.co = co

            targetVerts = list(coords.keys() - boundary)
        else:
            inside = [c for c in coords.keys() if not c.is_boundary]
            targetVerts = inside

        bmesh.ops.smooth_vert(
            self.bmo.bm,
            verts = targetVerts,
            factor = self.preferences.brush_strength,
            mirror_clip_x = is_fix_zero,
            mirror_clip_y = False,
            mirror_clip_z = False,
            clip_dist = 0.0001,
            use_axis_x = True,
            use_axis_y = True,
            use_axis_z = True)

        matrix_world = self.bmo.obj.matrix_world
        is_x_zero_pos = self.bmo.is_x_zero_pos
        zero_pos = self.bmo.zero_pos
        mirror_pos = self.bmo.mirror_pos
        for v , (f,orig) in coords.items():
            p = QSnap.adjust_local(matrix_world, v.co, is_fix_zero)
            s = orig.lerp(p, f)
            if is_fix_zero and is_x_zero_pos(s):
                s = zero_pos(s)
            v.co = s

        if self.bmo.is_mirror_mode:
            for vert , mirror in mirrors.items():
                if mirror == None:
                    continue
                if mirror in coords:
                    ms = coords[mirror][0]
                    vs = coords[vert][0]
                    if vs >= ms:
                        mirror.co = mirror_pos(vert.co)
                    else:
                        vert.co = mirror_pos(mirror.co)
                else:
                    mirror.co = mirror_pos(vert.co)

        bmesh.update_edit_mesh(self.bmo.obj.data, loop_triangles = False, destructive = False)

    def getAvgPos(self, le):
        tv = mathutils.Vector((0, 0, 0))
        for te in le:
            tv = tv + te
        ap = tv * (1 / len(le))
        return ap

    @classmethod
    def GetCursor(cls) :
        return 'CROSSHAIR'
