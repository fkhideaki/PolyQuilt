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
import bgl
import blf
import gpu
import bmesh
import math
import copy
import mathutils
import bpy_extras
import collections
from gpu_extras.batch import batch_for_shader
from .pqutil import *
from .dpi import *

vertex_shader = '''
    uniform mat4 viewProjectionMatrix;

    in vec3 pos;

    void main()
    {
        gl_Position = viewProjectionMatrix * vec4(pos, 1.0f);
    }
'''

fragment_shader = '''
    uniform vec4 color;

    void main()
    {
        gl_FragColor = color;
    }
'''



def begin_draw() :
    pass

def end_draw() :
    pass

def clear_draw() :
    pass
    
def batch_draw( shader , primitiveType , content  , indices = None ) :
    if indices :
        batch = batch_for_shader(shader, primitiveType , content , indices=indices )
    else :
        batch = batch_for_shader(shader, primitiveType , content )
    batch.draw(shader)
    return batch

#shader2D = gpu.types.GPUShader(vertex_shader, fragment_shader)
shader2D = gpu.shader.from_builtin('UNIFORM_COLOR')
shader3D = gpu.shader.from_builtin('UNIFORM_COLOR')

def gl_blend(enable):
    '''
    if enable:
        bgl.glEnable(bgl.GL_BLEND)
    else:
        bgl.glDisable(bgl.GL_BLEND)
    '''
    pass
def gl_line_smooth(enable):
    '''
    if enable:
        bgl.glEnable(bgl.GL_LINE_SMOOTH)
    else:
        bgl.glDisable(bgl.GL_LINE_SMOOTH)
    '''
    pass
def gl_depth_test(enable):
    '''
    if enable:
        bgl.glEnable(bgl.GL_DEPTH_TEST)
    else:
        bgl.glDisable(bgl.GL_DEPTH_TEST)
    '''
    pass
def gl_polygon_offset_line(enable):
    '''
    if enable:
        bgl.glEnable(bgl.GL_POLYGON_OFFSET_LINE)
    else:
        bgl.glDisable(bgl.GL_POLYGON_OFFSET_LINE)
    '''
    pass
def gl_polygon_offset_fill(enable):
    '''
    if enable:
        bgl.glEnable(bgl.GL_POLYGON_OFFSET_FILL)
    else:
        bgl.glDisable(bgl.GL_POLYGON_OFFSET_FILL)
    '''
    pass
def gl_polygon_offset_point(enable):
    '''
    if enable:
        bgl.glEnable(bgl.GL_POLYGON_OFFSET_POINT)
    else:
        bgl.glDisable(bgl.GL_POLYGON_OFFSET_POINT)
    '''
    pass
def gl_line_width(width):
    '''
    bgl.glLineWidth(width)
    '''
    pass
def gl_point_size(sz):
    '''
    bgl.glPointSize(width)
    '''
    pass
def gl_depth_mask(enable):
    '''
    if enable:
        bgl.glDepthMask(bgl.GL_TRUE)
    else:
        bgl.glDepthMask(bgl.GL_FALSE)
    '''
    pass
def gl_depthfunc_lequal():
    '''
    bgl.glDepthFunc(bgl.GL_LEQUAL)
    '''
    pass
def gl_depthfunc_always():
    '''
    bgl.glDepthFunc(bgl.GL_ALWAYS)
    '''
    pass
def gl_depthfunc_greater():
    '''
    bgl.glDepthFunc(bgl.GL_GREATER)
    '''
    pass
def gl_polygon_offset_1_1():
    '''
    bgl.glPolygonOffset(1.0, 1.0)
    '''
    pass

def draw_circle2D( pos , radius , color = (1,1,1,1), fill = False , subdivide = 64 , dpi = True, width : float = 1.0  ):
    if dpi :
        r = radius * dpm()
    else :
        r = radius
    dr = math.pi * 2 / subdivide
    vertices = [( pos[0] + r * math.cos(i*dr), pos[1] + r * math.sin(i*dr)) for i in range(subdivide+1)]

    gl_line_smooth(True)
    gl_line_width(width)
    gl_blend(True)
    gl_depth_test(False)
    shader2D.bind()
    shader2D.uniform_float("color", color )
    primitiveType = 'TRI_FAN' if fill else 'LINE_STRIP'
    batch_draw(shader2D, primitiveType , {"pos": vertices} )
    gl_line_width(1)
    gl_line_smooth(False)

def draw_donuts2D( pos , radius_out , width , rate , color = (1,1,1,1) ):
    r = radius_out * dpm()
    subdivide = 100
    t = int( max(min(rate,1),0)*subdivide)
    dr = math.pi * 2 / subdivide
    vertices = [( pos[0] + r * math.sin(i*dr), pos[1] + r * math.cos(i*dr)) for i in range(t+1)]

    draw_lines2D( vertices , (0,0,0,color[3]*0.5) , (width )* dpm()+ 1.0  )
    draw_lines2D( vertices , color , width* dpm()  )

def draw_lines2D( verts , color = (1,1,1,1) , width : float = 1.0 ):
    gl_line_smooth(True)
    gl_line_width(width)
    gl_blend(True)
    shader2D.bind()
    shader2D.uniform_float("color", color )
    batch_draw(shader2D, 'LINE_STRIP', {"pos": verts} )
    gl_line_width(1)
    gl_line_smooth(False)
    gl_blend(False)

def draw_poly2D( verts , color = (1,1,1,1) ):
    gl_line_smooth(True)
    gl_blend(True)
    shader2D.bind()
    shader2D.uniform_float("color", color )
    batch_draw(shader2D, 'TRIS', {"pos": verts} )
    gl_line_smooth(False)
    gl_blend(False)

def begin2d() :
    gl_depth_test(False)

def draw_loop3D(context, verts, color = (1,1,1,1), width : float = 1.0, hide_alpha : float = 1.0):
    draw_lines3D(context, verts, color, width, hide_alpha, 'LINE_LOOP')

def draw_lines3D(context, verts, color = (1,1,1,1), width : float = 1.0 , hide_alpha : float = 1.0 , primitiveType = 'LINE_STRIP' ):
    gl_line_smooth(True)
    gl_line_width(width)
    gl_blend(True)
    gl_depth_test(True)
    gl_depth_mask(False)
    gl_polygon_offset_line(True)
    gl_polygon_offset_fill(True)
    gl_polygon_offset_1_1()

    if hide_alpha < 0.99 :
        gl_depthfunc_lequal()
    else :
        gl_depthfunc_always()

#   shader3D.uniform_float("modelMatrix", Matrix.Identity(4) )
    shader3D.bind()
    matrix = context.region_data.perspective_matrix
#   shader3D.uniform_float("viewProjectionMatrix", matrix)
    shader3D.uniform_float("color", color )

    batch = batch_draw(shader3D, primitiveType , {"pos": verts} )

    if hide_alpha < 0.99 :
        gl_depthfunc_greater()
        shader3D.uniform_float("color", (color[0],color[1],color[2],color[3] * hide_alpha) )
        batch.draw(shader3D)

    gl_line_width(1)
    gl_line_smooth(False)
    gl_blend(False)
    gl_polygon_offset_line(False)
    gl_polygon_offset_fill(False)

def draw_Poly3D( context , verts , color = (1,1,1,1) , hide_alpha = 0.5 ):
    gl_blend(True)
    gl_depth_test(True)
    gl_depthfunc_lequal()
    gl_depth_mask(False)
    gl_polygon_offset_fill(True)
    gl_polygon_offset_1_1()

    polys = mathutils.geometry.tessellate_polygon( (verts,) )
    shader3D.bind()
    shader3D.uniform_float("color", color )
    batch = batch_draw(shader3D, 'TRIS', {"pos": verts } , indices=polys )

    if hide_alpha > 0.0 :
        gl_depthfunc_greater()
        shader3D.uniform_float("color", (color[0],color[1],color[2],color[3] * hide_alpha) )
        batch.draw(shader3D )

    gl_blend(False)
    gl_polygon_offset_fill(False)

def draw_pivots3D( poss , radius , color = (1,1,1,1) ):
    gl_blend(True)
    gl_line_smooth(False)
    gl_point_size(radius * dpm() * 2)
    gl_depth_test(False)
    gl_depth_mask(False)
    
    gl_polygon_offset_point(True)
    gl_polygon_offset_1_1()

    shader3D.bind()
    shader3D.uniform_float("color", color )
    batch_draw(shader3D, 'POINTS', {"pos": poss} )

    gl_point_size(1)
    gl_polygon_offset_point(False)

    gl_blend(True)
    gl_depth_test(False)
    gl_depth_mask(False)


def draw_Face3D( obj , face : bmesh.types.BMFace , color = (1,1,1,1) , isFill = True ):
    gl_blend(True)

    if isFill :
        vs = [ obj.matrix_world @ v.vert.co for v in face.loops ]
        polys = mathutils.geometry.tessellate_polygon( (vs,) )
        shader3D.bind()
        shader3D.uniform_float("color", color )
        batch_draw(shader3D, 'TRIS', {"pos": vs } , indices=polys )
    else :
        verts = []
        for edge in face.edges :
            verts.append( obj.matrix_world @ edge.verts[0].co )
            verts.append( obj.matrix_world @ edge.verts[1].co )
        shader3D.bind()
        shader3D.uniform_float("color", color )
        batch_draw(shader3D, 'LINES', {"pos": verts} )
    gl_blend(False)


def draw_Edge3D( obj , edge : bmesh.types.BMEdge , color = (1,1,1,1) , width = 1 ):
    gl_line_smooth(True)
    gl_line_width(width)
    gl_blend(True)
    gl_depthfunc_always()
    gl_depth_mask(False)

    verts = ( obj.matrix_world @ edge.verts[0].co ,  obj.matrix_world @ edge.verts[1].co )

    shader3D.bind()
    shader3D.uniform_float("color", color )
    batch = batch_for_shader(shader3D, 'LINES', {"pos": verts} )
    batch.draw(shader3D)
    gl_line_width(1)
    gl_line_smooth(False)
    gl_blend(False)


def drawElementsHilight3D( obj , elements, radius,width ,alpha, color = (1,1,1,1) ) :
    for element in elements :
        drawElementHilight3D(obj , element, radius ,width,alpha, color)

def drawElementsHilight3DFunc( obj , elements, radius,width ,alpha, color = (1,1,1,1) ) :
    funcs = [ drawElementHilight3DFunc(obj , e, radius ,width,alpha, color) for e in elements ]
    def func() :
        for f in funcs :
            f()
    return func

def drawElementHilight3D( obj , element, radius ,width , alpha, color = (1,1,1,1) ) :
    gl_blend(True)
    gl_depth_test(False)
    gl_depth_mask(False)

    if isinstance( element , bmesh.types.BMVert ) :
        v = obj.matrix_world @ element.co
        draw_pivots3D( (v,) , radius , color )
    elif isinstance( element , bmesh.types.BMFace  ) :
        draw_Face3D(obj,element, (color[0],color[1],color[2],color[3] * alpha) )
    elif isinstance( element , bmesh.types.BMEdge ) :
        draw_Edge3D(obj,element,color,width)

    gl_depth_test(True)
    gl_blend(False)
    gl_depth_mask(False)

def drawElementHilight3DFunc(obj, element, radius, width, alpha, color = (1,1,1,1)):
    matrix_world = copy.copy(obj.matrix_world)

    if isinstance(element, bmesh.types.BMVert):
        co = copy.copy(element.co)
        v = matrix_world @ co
        def draw():
            draw_pivots3D((v,), radius, color)
        return draw

    elif isinstance(element, bmesh.types.BMFace):
        vs = [ matrix_world @ v.vert.co for v in element.loops ]
        polys = mathutils.geometry.tessellate_polygon( (vs,) )
        def draw() :
            gl_blend(True)
            gl_depth_test(False)
            gl_depth_mask(False)

            shader3D.bind()
            shader3D.uniform_float("color",  (color[0],color[1],color[2],color[3] * alpha) )
            batch_draw(shader3D, 'TRIS', {"pos": vs } , indices=polys )
            gl_blend(False)
            gl_depth_test(False)
            gl_depth_mask(False)
        return draw

    elif isinstance( element , bmesh.types.BMEdge ) :
        verts = ( matrix_world @ element.verts[0].co ,  matrix_world @ element.verts[1].co )
        def draw() :
            gl_blend(True)

            gl_line_smooth(True)
            gl_line_width(width)
            gl_depthfunc_always()
            gl_depth_mask(False)

            shader3D.bind()
            shader3D.uniform_float("color", color )
            batch = batch_for_shader(shader3D, 'LINES', {"pos": verts} )
            batch.draw(shader3D)
            gl_line_width(1)
            gl_line_smooth(False)
            gl_blend(False)
        return draw

    return None



def DrawFont( text , size , positon , offset = (0,0) ) :
    font_id = 0
    blf.size(font_id, size, dpi() )
    w,h = blf.dimensions(font_id, text )
    blf.position(font_id, positon[0] - w / 2 + offset[0] * dpm() , positon[1] + h + offset[1] * dpm() , 0)
    blf.draw(font_id, text )


def make_mat4_ortho( left, right, bottom, top, _near = - 100, _far = 100) :
    return mathutils.Matrix(
        (
        (2.0 / (right - left),0,0,-(right + left) / (right - left)) ,
        (0,2.0 / (top - bottom),0,-(top + bottom) / (top - bottom)) ,
        (0,0,-2.0 / (_far - _near),-(_far + _near) / (_far - _near)) ,
        (0,0,0,1) )
        )

class push_pop_projection2D:
    def __enter__(self):
        region = bpy.context.region   
        matrix = make_mat4_ortho(0, region.width, 0, region.height)
        gpu.matrix.push()
        gpu.matrix.push_projection()
        gpu.matrix.load_projection_matrix( matrix )
        gpu.matrix.load_identity()
        return self
    def __exit__(self, exc_type, exc_value, traceback):
        gpu.matrix.pop()
        gpu.matrix.pop_projection()
        if (exc_type!=None):
            #return True  #例外を抑制するには
            return False #例外を伝播する
