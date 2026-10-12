# SPDX-License-Identifier: GPL-3.0-or-later
"""Screen-space style effects shared by live views and image exports."""
from __future__ import annotations
import math


def image_rect(image_width, image_height, view_width, view_height, position, scale=.25):
    """Image placement in logical pixels; scaling keeps its aspect ratio."""
    if position == 'stretch':
        return (0., 0., float(view_width), float(view_height))
    width = max(1., view_width * max(.01, min(2., float(scale))))
    height = width * image_height / max(image_width, 1)
    if height > view_height and position != 'tile':
        width *= view_height/height
        height = float(view_height)
    margin = 8.
    x = margin if position.endswith('left') else view_width-width-margin
    y = margin if position.startswith('top') else view_height-height-margin
    if position == 'center':
        x, y = (view_width-width)*.5, (view_height-height)*.5
    if position == 'tile':
        x = y = 0.
    return (x, y, width, height)


def ambient_occlusion(depth, inverse_projection, distance=1., intensity=.5, multiplier=1., max_size=480):
    """Bounded SSAO from reconstructed view-space positions.

    Eight neighbour directions at two radii, a tangent-plane bias, range
    attenuation and explicit border masks prevent flat planes and the image
    borders being mistaken for corners. Output is an alpha map, top first.
    Calculation uses a reduced depth image; disabled styles pay no cost.
    """
    import numpy as np
    full_height, full_width = depth.shape
    step = max(1, math.ceil(max(full_height, full_width)/max_size))
    z = depth[::step, ::step].astype(np.float64)
    h, w = z.shape
    if h < 3 or w < 3:
        return np.zeros((h, w), dtype=np.uint8)
    yy, xx = np.mgrid[0:h, 0:w]
    ndc = np.stack(((xx*step+.5)/full_width*2-1,
                    (yy*step+.5)/full_height*2-1, z*2-1, np.ones_like(z)), axis=-1)
    coords = ndc @ np.asarray(inverse_projection).T
    denom = coords[..., 3:4]
    points = coords[..., :3] / np.where(abs(denom)>1e-12, denom, 1.)
    dx = np.gradient(points, axis=1)
    dy = np.gradient(points, axis=0)
    normal = np.cross(dx, dy)
    norm = np.linalg.norm(normal, axis=-1, keepdims=True)
    normal /= np.maximum(norm, 1e-12)
    # Normals point toward the camera even for reversed face winding.
    normal *= np.where(np.sum(normal * -points, axis=-1, keepdims=True) >= 0, 1, -1)
    valid = (z < .999999) & np.isfinite(points).all(axis=-1)
    radius = max(.001, float(distance)*float(multiplier))
    world_per_pixel = np.maximum(np.linalg.norm(dx, axis=-1), 1e-6)
    pixel_radius = int(np.clip(np.median(radius/world_per_pixel[valid]) if valid.any() else 1, 1, 24))
    total = np.zeros((h, w))
    weights = np.zeros((h, w))
    for amount in (max(1, pixel_radius//2), pixel_radius):
        for sx, sy in ((1,0),(-1,0),(0,1),(0,-1),(1,1),(-1,1),(1,-1),(-1,-1)):
            ox, oy = sx*amount, sy*amount
            neighbor = np.roll(points, (oy,ox), axis=(0,1))
            neighbor_valid = np.roll(valid, (oy,ox), axis=(0,1))
            if oy > 0: neighbor_valid[:oy,:] = False
            if oy < 0: neighbor_valid[oy:,:] = False
            if ox > 0: neighbor_valid[:,:ox] = False
            if ox < 0: neighbor_valid[:,ox:] = False
            delta = neighbor-points
            length = np.linalg.norm(delta, axis=-1)
            height = np.sum(delta*normal, axis=-1)
            bias = np.maximum(.002*radius, world_per_pixel*.02)
            angle = np.maximum((height-bias)/np.maximum(length,1e-9),0)
            attenuation = np.maximum(1-length/radius,0)
            sample = valid & neighbor_valid
            total += angle * attenuation * sample
            weights += sample
    alpha = np.clip(total/np.maximum(weights,1)*float(intensity)*4,0,.85)
    alpha[~valid] = 0
    # GL's origin is bottom-left; QImage's is top-left.
    return np.ascontiguousarray((alpha[::-1]*255).astype(np.uint8))


def profile_mesh_data(mesh, visible):
    """Cache the hard edges' adjacent face planes in mesh coordinates."""
    import numpy as np
    edges = [edge for edge in mesh.edges if visible(edge) and not edge.hidden
             and not edge.soft and edge.faces]
    if not edges:
        return None
    face_planes = {}
    def plane(face):
        if face not in face_planes:
            face_planes[face] = (face.normal().toTuple(), face.loop[0].position.toTuple())
        return face_planes[face]
    segments, normal0, center0, normal1, center1, single = [], [], [], [], [], []
    for edge in edges:
        faces = [face for face in edge.faces if visible(face)]
        if not faces:
            continue
        n0,c0 = plane(faces[0])
        n1,c1 = plane(faces[1]) if len(faces)>1 else (n0,c0)
        segments.append((edge.a.toTuple(),edge.b.toTuple()))
        normal0.append(n0);center0.append(c0);normal1.append(n1);center1.append(c1)
        single.append(len(faces)==1)
    return (np.asarray(segments,dtype=np.float32),np.asarray(normal0),np.asarray(center0),
            np.asarray(normal1),np.asarray(center1),np.asarray(single,dtype=bool)) if segments else None


def profile_segments(data, eye):
    """Boundary edges and edges whose faces straddle the viewing direction."""
    import numpy as np
    segments,n0,c0,n1,c1,single = data
    s0 = np.einsum('ij,ij->i',n0,c0-np.asarray(eye))
    s1 = np.einsum('ij,ij->i',n1,c1-np.asarray(eye))
    return segments[single | ((s0<0)!=(s1<0))]
