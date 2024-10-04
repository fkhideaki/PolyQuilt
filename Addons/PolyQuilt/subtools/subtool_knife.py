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
import blf
import math
import mathutils
import bmesh
import bpy_extras
import collections
from ..utils import pqutil
from ..utils import draw_util
from ..QMesh import *
from .subtool import SubTool

class SubToolKnife(SubTool) :
    name = "KnifeTool2"

    def __init__(self,op, currentElement : ElementItem ,startPos) :
        super().__init__(op)
        if currentElement.isNotEmpty and not currentElement.isFace :
            self.startPos = currentElement.coord
        else :
            self.startPos = startPos
        self.endPos = self.startPos
        self.cut_edges = {}
        self.cut_edges_mirror = {}
        self.startElement = currentElement
        self.goalElement = ElementItem.Empty()

    def OnUpdate( self , context , event ) :
        self.goalElement = self.bmo.PickElement( self.mouse_pos , self.preferences.distance_to_highlight, elements = ['EDGE','VERT'] )   
        if self.goalElement.isNotEmpty and not self.goalElement.isFace :
            self.goalElement.set_snap_div( self.preferences.loopcut_division )
            self.endPos = self.goalElement.coord
        else :
            self.endPos = self.mouse_pos
        
        if event.type == 'MOUSEMOVE':
            if( self.startPos - self.endPos ).length > 2 :
                self.CalcKnife(context, self.startPos, self.endPos)
        elif event.type == 'RIGHTMOUSE' :
            if event.value == 'RELEASE' :
                return 'FINISHED'
        elif event.type == 'LEFTMOUSE' : 
            if event.value == 'RELEASE' :
                if self.cut_edges or self.cut_edges_mirror  :
                    self.DoKnife(context,self.startPos,self.endPos)
                    self.bmo.UpdateMesh()                
                    return 'FINISHED'
                return 'CANCELLED'
        return 'RUNNING_MODAL'

    def OnDraw( self , context  ) :
        draw_util.draw_lines2D( (self.startPos,self.endPos) , self.color_delete() , self.preferences.highlight_line_width )

    def OnDraw3D( self , context  ) :
        if self.goalElement.isNotEmpty :
            self.goalElement.Draw( self.bmo.obj , self.color_highlight() , self.preferences )

        if self.cut_edges :
            draw_util.draw_pivots3D( list(self.cut_edges.values()) , 1 , self.color_delete() )
        if self.cut_edges_mirror :
            draw_util.draw_pivots3D( list(self.cut_edges_mirror.values()) , 1 , self.color_delete(0.5) )

    def CalcKnife(self, context, e0, e1) :
        slice_plane, plane0, plane1, ray0, ray1 = self.make_slice_planes(context, e0, e1)
        self.cut_edges = self.calc_slice(slice_plane, plane0, plane1, ray0, ray1)
        if self.bmo.is_mirror_mode :
            slice_plane.x_mirror()
            plane0.x_mirror()
            plane1.x_mirror()
            self.cut_edges_mirror = self.calc_slice(slice_plane, plane0, plane1, ray0, ray1)

    def make_slice_planes(self, context, e0, e1):
        obj = self.bmo.obj
        slice_plane_world = pqutil.Plane.from_screen_slice(context, e0, e1)
        slice_plane = slice_plane_world.world_to_object(obj)

        ray0 = pqutil.Ray.from_screen(context, e0).world_to_object(obj)
        ray1 = pqutil.Ray.from_screen(context, e1).world_to_object(obj)
        vec0 = slice_plane.vector.cross(ray0.vector).normalized()
        vec1 = slice_plane.vector.cross(ray1.vector).normalized()
        plane0 = pqutil.Plane(ray0.origin - vec0 * 0.001, vec0)
        plane1 = pqutil.Plane(ray1.origin + vec1 * 0.001, vec1)

        return slice_plane, plane0, plane1, ray0, ray1

    def calc_slice(self, slice_plane, plane0, plane1, ray0, ray1):
        rv0 = ray0.vector
        rv1 = ray1.vector
        rvm = rv0 + rv1
        slice_plane_intersect_line = slice_plane.intersect_line
        plane0_distance_point = plane0.distance_point
        plane1_distance_point = plane1.distance_point
        epsilon = sys.float_info.epsilon

        matrix = self.bmo.obj.matrix_world
        ed = {}
        for edge in self.bmo.edges:
            if edge.hide:
                continue

            v0 = edge.verts[0]
            v1 = edge.verts[1]

            if self.preferences.knife_only_select:
                if not edge.select:
                    continue

            p0 = v0.co
            p1 = v1.co
            p = slice_plane_intersect_line(p0, p1)
            if not p:
                continue

            a0 = plane0_distance_point(p)
            a1 = plane1_distance_point(p)
            if (a0 > epsilon and a1 > epsilon):
                continue
            if (a0 < -epsilon and a1 < -epsilon):
                continue

            ed[edge] = matrix @ p
        return ed

    def DoKnife(self, context, e0, e1 ) :
        bm = self.bmo.bm
        threshold = bpy.context.scene.tool_settings.double_threshold
        plane, plane0, plane1, ray0, ray1 = self.make_slice_planes(context, e0, e1)
        faces = [ face for face in self.bmo.faces if not face.hide ]
        elements = list(self.cut_edges.keys()) + faces

        ret = bmesh.ops.bisect_plane(
            bm,
            geom=elements,
            dist=threshold,
            plane_co=plane.origin,
            plane_no=plane.vector,
            use_snap_center=True,
            clear_outer=False,
            clear_inner=False)
        for e in ret['geom_cut'] :
            e.select_set(True)
        return
        if QSnap.is_active() :
            QSnap.adjust_verts( self.bmo.obj , [ v for v in ret['geom_cut'] if isinstance( v , bmesh.types.BMVert ) ] , self.preferences.fix_to_x_zero )

        if self.bmo.is_mirror_mode :
            slice_plane, plane0, plane1, ray0, ray1 = self.make_slice_planes(context,e0 , e1)
            slice_plane.x_mirror()
            plane0.x_mirror()
            plane1.x_mirror()
            self.bmo.UpdateMesh()
            cut_edges_mirror = self.calc_slice(slice_plane, plane0, plane1, ray0, ray1)
            if cut_edges_mirror :
                faces = [ face for face in self.bmo.faces if face.hide is False ]
                elements = list(cut_edges_mirror.keys()) + faces[:]
                ret = bmesh.ops.bisect_plane(bm,geom=elements,dist=threshold,plane_co= slice_plane.origin ,plane_no= slice_plane.vector ,use_snap_center=False,clear_outer=False,clear_inner=False)
                for e in ret['geom_cut'] :
                    e.select_set(True)
                    if QSnap.is_active() :
                        QSnap.adjust_verts( self.bmo.obj , [ v for v in ret['geom_cut'] if isinstance( v , bmesh.types.BMVert ) ] , self.preferences.fix_to_x_zero )

    @classmethod
    def GetCursor(cls) :
        return 'KNIFE'
