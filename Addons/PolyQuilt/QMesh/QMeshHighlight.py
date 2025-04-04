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

import bpy
import mathutils
from mathutils import *
import numpy as np
from ..utils import pqutil
from ..utils.dpi import *
from .ElementItem import ElementItem

__all__ = ['QMeshHighlight']

class QMeshHighlight :
    __grobal_tag__ = 0

    def __init__(self, pqo) :
        self.pqo = pqo
        self.__viewPosVerts = None
        self.__viewPosEdges = None
        self.current_matrix = None
        self.__boundaryViewPosVerts = None
        self.__boundaryViewPosEdges = None
        self.__local_tag__ = 0

    @property
    def viewPosVerts(self):
        self.checkDirty()
        if self.__viewPosVerts == None :
            self.UpdatViewHighlight(bpy.context, True)
        return self.__viewPosVerts

    @property
    def viewPosEdges(self):
        self.checkDirty()
        if self.__viewPosEdges == None:
            self.UpdatViewHighlight(bpy.context, True)
        return self.__viewPosEdges

    @property
    def boundaryViewPosVerts(self):
        self.checkDirty()
        if self.__boundaryViewPosVerts == None :
            self.__boundaryViewPosVerts = [ ( v , p ) for v,p in self.viewPosVerts.items() if v.is_boundary or v.is_wire or not v.is_manifold ]           
        return self.__boundaryViewPosVerts

    @property
    def boundaryViewPosEdges(self):
        self.checkDirty()
        if self.__boundaryViewPosEdges == None :
            self.__boundaryViewPosEdges = { e : p for e , p in self.viewPosEdges.items() if e.is_boundary or e.is_wire }
        return self.__boundaryViewPosEdges

    def setDirty(self):
        QMeshHighlight.__grobal_tag__ = QMeshHighlight.__grobal_tag__ + 1
        self.checkDirty()

    def checkDirty(self):
        if QMeshHighlight.__grobal_tag__ == self.__local_tag__:
            return
        if self.__viewPosVerts:
            del self.__viewPosVerts
        self.__viewPosVerts = None

        if self.__viewPosEdges:
            del self.__viewPosEdges
        self.__viewPosEdges = None

        if self.__boundaryViewPosVerts:
            del self.__boundaryViewPosVerts
        self.__boundaryViewPosVerts = None

        if self.__boundaryViewPosEdges:
            del self.__boundaryViewPosEdges
        self.__boundaryViewPosEdges = None

        self.current_matrix = None
        self.__local_tag__ = QMeshHighlight.__grobal_tag__

    def UpdatViewHighlight(self, context, forced):
        rv3d = context.region_data
        pj_matrix = rv3d.perspective_matrix @ self.pqo.obj.matrix_world
        self.checkDirty()

        if not forced and pj_matrix == self.current_matrix:
            return

        region = context.region
        halfW = region.width / 2.0
        halfH = region.height / 2.0
        mat_scaleX = mathutils.Matrix.Scale(halfW, 4, (1.0, 0.0, 0.0))
        mat_scaleY = mathutils.Matrix.Scale(halfH, 4, (0.0, 1.0, 0.0))
        matrix = mat_scaleX @ mat_scaleY @ pj_matrix
        halfWH = Vector((halfW, halfH))

        pqbm = self.pqo.bm

        viewPos = {}
        for p in pqbm.verts:
            pv = matrix @ p.co.to_4d()
            if pv[3] > 0.0:
                v2 = pv.to_2d() / pv[3] + halfWH
                viewPos[p] = v2

        viewEdges = {}
        for e in pqbm.edges:
            if e.hide:
                continue
            ev0 = e.verts[0]
            ev1 = e.verts[1]
            if not ev0 in viewPos or not ev1 in viewPos:
                continue
            p0 = viewPos[ev0]
            p1 = viewPos[ev1]
            viewEdges[e] = [p0, p1]

        self.__viewPosEdges = viewEdges
        self.__viewPosVerts = { v : p for v, p in viewPos.items() if p and not v.hide }
        self.__boundaryViewPosEdges = None
        self.__boundaryViewPosVerts = None

        self.current_matrix = pj_matrix


    def CollectVerts(self, coord, radius : float, ignore = [], edgering = False, backface_culling = True) -> ElementItem :
        p = Vector(coord)
        rr = Vector((radius, 0))

        pqbm = self.pqo.bm
        verts = pqbm.verts
        viewPos = self.viewPosVerts

        ray = None
        if backface_culling:
            ray = pqutil.Ray.from_screen(bpy.context, coord).world_to_object(self.pqo.obj)

        s = []
        for v, vs in viewPos.items():
            if v in ignore:
                continue
            if not (vs - p <= rr and v in verts):
                continue
            if edgering:
                if not (v.is_boundary or not v.is_manifold):
                    continue
            if backface_culling:
                if v.is_manifold:
                    if not v.is_boundary and v.normal.dot(ray.vector) >= 0:
                        continue
            s.append([v, vs])

        r = sorted(s, key=lambda i:(i[1] - p).length_squared)
        matrix_world = self.pqo.obj.matrix_world

        tr = []
        for i in r:
            trv = ElementItem(self.pqo, i[0], i[1], matrix_world @ i[0].co)
            tr.append(trv)
        return tr


    def CollectEdge( self ,coord , radius : float , ignore = [] , backface_culling = True , edgering = False ) -> ElementItem :
        p = Vector( coord )
        viewPosEdge = self.viewPosEdges
        ray = pqutil.Ray.from_screen( bpy.context , coord )
        ray_distance = ray.distance
        location_3d_to_region_2d = pqutil.location_3d_to_region_2d
        intersect_point_line = geometry.intersect_point_line
        matrix_world = self.pqo.obj.matrix_world      
        rr = Vector( (radius,0) )

        def Conv( edge ) -> ElementItem :
            v1 = matrix_world @ edge.verts[0].co
            v2 = matrix_world @ edge.verts[1].co
            h0 , h1 , d = ray_distance( pqutil.Ray( v1 , (v1-v2) ) )
            c = location_3d_to_region_2d(h1)
            return ElementItem( self.pqo , edge , c , h1 , d )

        def intersect( p1 , p2 ) :
            hit , pt = intersect_point_line( p , p1 , p2 )
            if pt > 0 and pt < 1 :
                if hit - p <= rr :
                    return True
            return False

        pqbm = self.pqo.bm
        edges = pqbm.edges
        if edgering :
            r = [ Conv(e) for e,(p1,p2) in viewPosEdge.items() if len(e.link_faces) <= 1 and intersect( p1 , p2 ) and e not in ignore ]
        else :
            r = [ Conv(e) for e,(p1,p2) in viewPosEdge.items() if intersect( p1 , p2 ) and e in edges and e not in ignore ]

        if backface_culling :
            ray2 = ray.world_to_object( self.pqo.obj )
            r = [ i for i in r
                if not i.element.is_manifold or i.element.is_boundary or
                    i.element.verts[0].normal.dot( ray.vector ) < 0 or i.element.verts[1].normal.dot( ray2.vector ) < 0 ]

        s = sorted( r , key=lambda i:(i.coord - p).length_squared )
        return s


    def PickFace(self, coord, ignore = [], backface_culling = True) -> ElementItem:
        ray = pqutil.Ray.from_screen(bpy.context, coord).world_to_object(self.pqo.obj)
        pos, nrm, index, dist = self.pqo.btree.ray_cast(ray.origin, ray.vector)
        prePos = ray.origin
        pqbm = self.pqo.bm
        while (index is not None):
            face = pqbm.faces[index]
            if (prePos - pos).length < 0.00001:
                break
            prePos = pos
            if face.hide is False and face not in ignore:
                if backface_culling == False or face.normal.dot(ray.vector) < 0:
                    return ElementItem(self.pqo, face, coord, self.pqo.obj.matrix_world @ pos, dist)
                else:
                    return ElementItem.Empty()
            ray.origin = ray.origin + ray.vector * 0.00001
            pos, nrm, index, dist = self.pqo.btree.ray_cast(ray.origin, ray.vector)

        return ElementItem.Empty()


    def check_hit_element_vert( self , element , mouse_pos ,radius ) :
        rv3d = bpy.context.region_data
        region = bpy.context.region
        halfW = region.width / 2.0
        halfH = region.height / 2.0
        mat_scaleX = mathutils.Matrix.Scale( halfW , 4 , (1.0, 0.0, 0.0))
        mat_scaleY = mathutils.Matrix.Scale( halfH , 4 , (0.0, 1.0, 0.0))
        matrix = mat_scaleX @ mat_scaleY @ rv3d.perspective_matrix @ self.pqo.obj.matrix_world
        halfWH = Vector( (halfW,halfH) )
        def ProjVert( vt ) :
            pv = matrix @ vt.co.to_4d()
            return pv.to_2d() / pv[3] + halfWH if pv[3] > 0.0 else None

        for v in element.verts :
            co = ProjVert( v )
            if ( mouse_pos - co ).length <= radius :
                return v

        return None

    def check_hit_element_edge( self , element , mouse_pos ,radius ) :
        rv3d = bpy.context.region_data
        region = bpy.context.region
        halfW = region.width / 2.0
        halfH = region.height / 2.0
        mat_scaleX = mathutils.Matrix.Scale( halfW , 4 , (1.0, 0.0, 0.0))
        mat_scaleY = mathutils.Matrix.Scale( halfH , 4 , (0.0, 1.0, 0.0))
        matrix = mat_scaleX @ mat_scaleY @ rv3d.perspective_matrix @ self.pqo.obj.matrix_world
        halfWH = Vector( (halfW,halfH) )
        def ProjVert( vt ) :
            pv = matrix @ vt.co.to_4d()
            return pv.to_2d() / pv[3] + halfWH if pv[3] > 0.0 else None

        intersect_point_line = geometry.intersect_point_line
        rr = Vector( (radius,0) )
        def intersect( p1 , p2 ) :
            hit , pt = intersect_point_line( mouse_pos , p1 , p2 )
            if pt > 0 and pt < 1 :
                if hit - mouse_pos <= rr :
                    return True

        for e in element.edges :
            co0 = ProjVert( e.verts[0] )
            co1 = ProjVert( e.verts[1] )
            if intersect(co0,co1) :
                return e

        return None
