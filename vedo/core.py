#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import numpy as np

try:
    import vedo.vtkclasses as vtk
except ImportError:
    import vtkmodules.all as vtk

import vedo
from vedo import colors
from vedo import utils
from vedo.transformations import LinearTransform


__docformat__ = "google"

__doc__ = "Base classes providing functionality to all vedo objects."

__all__ = ["CommonAlgorithms", "PointAlgorithms", "VolumeAlgorithms"]


###############################################################################
class DataArrayHelper:
    # Internal use only.
    # Helper class to manage data associated to either
    # points (or vertices) and cells (or faces).
    def __init__(self, obj, association):

        self.obj = obj
        self.association = association

    def __getitem__(self, key):

        if self.association == 0:
            data = self.obj.dataset.GetPointData()

        elif self.association == 1:
            data = self.obj.dataset.GetCellData()

        elif self.association == 2:
            data = self.obj.dataset.GetFieldData()

            varr = data.GetAbstractArray(key)
            if isinstance(varr, vtk.vtkStringArray):
                if isinstance(key, int):
                    key = data.GetArrayName(key)
                n = varr.GetNumberOfValues()
                narr = [varr.GetValue(i) for i in range(n)]
                return narr
                ###########

        else:
            raise RuntimeError()

        if isinstance(key, int):
            key = data.GetArrayName(key)

        arr = data.GetArray(key)
        if not arr:
            return None
        return utils.vtk2numpy(arr)

    def __setitem__(self, key, input_array):

        if self.association == 0:
            data = self.obj.dataset.GetPointData()
            n = self.obj.dataset.GetNumberOfPoints()
            self.obj.mapper.SetScalarModeToUsePointData()

        elif self.association == 1:
            data = self.obj.dataset.GetCellData()
            n = self.obj.dataset.GetNumberOfCells()
            self.obj.mapper.SetScalarModeToUseCellData()

        elif self.association == 2:
            data = self.obj.dataset.GetFieldData()
            if not utils.is_sequence(input_array):
                input_array = [input_array]

            if isinstance(input_array[0], str):
                varr = vtk.vtkStringArray()
                varr.SetName(key)
                varr.SetNumberOfComponents(1)
                varr.SetNumberOfTuples(len(input_array))
                for i, iarr in enumerate(input_array):
                    if isinstance(iarr, np.ndarray):
                        iarr = iarr.tolist()  # better format
                        # Note: a string k can be converted to numpy with
                        # import json; k = np.array(json.loads(k))
                    varr.InsertValue(i, str(iarr))
            else:
                try:
                    varr = utils.numpy2vtk(input_array, name=key)
                except TypeError as e:
                    vedo.logger.error(
                        f"cannot create metadata with input object:\n"
                        f"{input_array}"
                        f"\n\nAllowed content examples are:\n"
                        f"- flat list of strings ['a','b', 1, [1,2,3], ...]"
                        f" (first item must be a string in this case)\n"
                        f"  hint: use k = np.array(json.loads(k)) to convert strings\n"
                        f"- numpy arrays of any shape"
                    )
                    raise e

            data.AddArray(varr)
            return  ############

        else:
            raise RuntimeError()

        if len(input_array) != n:
            vedo.logger.error(
                f"Error in point/cell data: length of input {len(input_array)}"
                f" !=  {n} nr. of elements"
            )
            raise RuntimeError()

        input_array = np.asarray(input_array)
        varr = utils.numpy2vtk(input_array, name=key)
        data.AddArray(varr)

        if len(input_array.shape) == 1:  # scalars
            data.SetActiveScalars(key)
        elif len(input_array.shape) == 2 and input_array.shape[1] == 3:  # vectors
            if key.lower() == "normals":
                data.SetActiveNormals(key)
            else:
                data.SetActiveVectors(key)

    def keys(self):
        """Return the list of available data array names"""
        if self.association == 0:
            data = self.obj.dataset.GetPointData()
        elif self.association == 1:
            data = self.obj.dataset.GetCellData()
        elif self.association == 2:
            data = self.obj.dataset.GetFieldData()
        arrnames = []
        for i in range(data.GetNumberOfArrays()):
            name = data.GetArray(i).GetName()
            if name:
                arrnames.append(name)
        return arrnames

    def remove(self, key):
        """Remove a data array by name or number"""
        if self.association == 0:
            self.obj.dataset.GetPointData().RemoveArray(key)
        elif self.association == 1:
            self.obj.dataset.GetCellData().RemoveArray(key)
        elif self.association == 2:
            self.obj.dataset.GetFieldData().RemoveArray(key)

    def clear(self):
        """Remove all data associated to this object"""
        if self.association == 0:
            data = self.obj.dataset.GetPointData()
        elif self.association == 1:
            data = self.obj.dataset.GetCellData()
        elif self.association == 2:
            data = self.obj.dataset.GetFieldData()
        for i in range(data.GetNumberOfArrays()):
            name = data.GetArray(i).GetName()
            data.RemoveArray(name)

    def rename(self, oldname, newname):
        """Rename an array"""
        if self.association == 0:
            varr = self.obj.dataset.GetPointData().GetArray(oldname)
        elif self.association == 1:
            varr = self.obj.dataset.GetCellData().GetArray(oldname)
        elif self.association == 2:
            varr = self.obj.dataset.GetFieldData().GetArray(oldname)
        if varr:
            varr.SetName(newname)
        else:
            vedo.logger.warning(
                f"Cannot rename non existing array {oldname} to {newname}"
            )

    def select(self, key):
        """Select one specific array by its name to make it the `active` one."""
        if self.association == 0:
            data = self.obj.dataset.GetPointData()
            self.obj.mapper.SetScalarModeToUsePointData()
        else:
            data = self.obj.dataset.GetCellData()
            self.obj.mapper.SetScalarModeToUseCellData()

        if isinstance(key, int):
            key = data.GetArrayName(key)

        arr = data.GetArray(key)
        if not arr:
            return

        nc = arr.GetNumberOfComponents()
        if nc == 1:
            data.SetActiveScalars(key)
        elif nc >= 2:
            if "rgb" in key.lower():
                data.SetActiveScalars(key)
                # try:
                #     self.mapper.SetColorModeToDirectScalars()
                # except AttributeError:
                #     pass
            else:
                data.SetActiveVectors(key)
        elif nc >= 4:
            data.SetActiveTensors(key)

        try:
            self.obj.mapper.SetArrayName(key)
            self.obj.mapper.ScalarVisibilityOn()
            # .. could be a volume mapper
        except AttributeError:
            pass

    def select_scalars(self, key):
        """Select one specific scalar array by its name to make it the `active` one."""
        if self.association == 0:
            data = self.obj.dataset.GetPointData()
            self.obj.mapper.SetScalarModeToUsePointData()
        else:
            data = self.obj.dataset.GetCellData()
            self.obj.mapper.SetScalarModeToUseCellData()

        if isinstance(key, int):
            key = data.GetArrayName(key)

        data.SetActiveScalars(key)

        try:
            self.obj.mapper.SetArrayName(key)
            self.obj.mapper.ScalarVisibilityOn()
        except AttributeError:
            pass

    def select_vectors(self, key):
        """Select one specific vector array by its name to make it the `active` one."""
        if self.association == 0:
            data = self.obj.dataset.GetPointData()
            self.obj.mapper.SetScalarModeToUsePointData()
        else:
            data = self.obj.dataset.GetCellData()
            self.obj.mapper.SetScalarModeToUseCellData()

        if isinstance(key, int):
            key = data.GetArrayName(key)

        data.SetActiveVectors(key)

        try:
            self.obj.mapper.SetArrayName(key)
            self.obj.mapper.ScalarVisibilityOn()
        except AttributeError:
            pass

    def print(self, **kwargs):
        """Print the array names available to terminal"""
        colors.printc(self.keys(), **kwargs)

    def __repr__(self) -> str:
        """Representation"""

        def _get_str(pd, header):
            out = f"\x1b[2m\x1b[1m\x1b[7m{header}"
            if pd.GetNumberOfArrays():
                if self.obj.name:
                    out += f" in {self.obj.name}"
                out += f" contains {pd.GetNumberOfArrays()} array(s)\x1b[0m"
                for i in range(pd.GetNumberOfArrays()):
                    varr = pd.GetArray(i)
                    out += f"\n\x1b[1m\x1b[4mArray name    : {varr.GetName()}\x1b[0m"
                    out += "\nindex".ljust(15) + f": {i}"
                    t = varr.GetDataType()
                    if t in vedo.utils.array_types:
                        out += f"\ntype".ljust(15)
                        out += f": {vedo.utils.array_types[t][1]} ({vedo.utils.array_types[t][0]})"
                    shape = (varr.GetNumberOfTuples(), varr.GetNumberOfComponents())
                    out += "\nshape".ljust(15) + f": {shape}"
                    out += "\nrange".ljust(15) + f": {np.array(varr.GetRange())}"
                    out += "\nmax id".ljust(15) + f": {varr.GetMaxId()}"
                    out += "\nlook up table".ljust(15) + f": {bool(varr.GetLookupTable())}"
                    out += "\nin-memory size".ljust(15) + f": {varr.GetActualMemorySize()} KB"
            else:
                out += " is empty.\x1b[0m"
            return out

        if self.association == 0:
            out = _get_str(self.obj.dataset.GetPointData(), "Point Data")
        elif self.association == 1:
            out = _get_str(self.obj.dataset.GetCellData(), "Cell Data")
        elif self.association == 2:
            pd = self.obj.dataset.GetFieldData()
            if pd.GetNumberOfArrays():
                out = f"\x1b[2m\x1b[1m\x1b[7mMeta Data"
                if self.actor.name:
                    out += f" in {self.actor.name}"
                out += f" contains {pd.GetNumberOfArrays()} entries\x1b[0m"
                for i in range(pd.GetNumberOfArrays()):
                    varr = pd.GetAbstractArray(i)
                    out += f"\n\x1b[1m\x1b[4mEntry name    : {varr.GetName()}\x1b[0m"
                    out += "\nindex".ljust(15) + f": {i}"
                    shape = (varr.GetNumberOfTuples(), varr.GetNumberOfComponents())
                    out += "\nshape".ljust(15) + f": {shape}"

        return out


###############################################################################
class CommonAlgorithms:
    """Common algorithms."""

    @property
    def pointdata(self):
        """
        Create and/or return a `numpy.array` associated to points (vertices).
        A data array can be indexed either as a string or by an integer number.
        E.g.:  `myobj.pointdata["arrayname"]`

        Usage:

            `myobj.pointdata.keys()` to return the available data array names

            `myobj.pointdata.select(name)` to make this array the active one

            `myobj.pointdata.remove(name)` to remove this array
        """
        return DataArrayHelper(self, 0)

    @property
    def celldata(self):
        """
        Create and/or return a `numpy.array` associated to cells (faces).
        A data array can be indexed either as a string or by an integer number.
        E.g.:  `myobj.celldata["arrayname"]`

        Usage:

            `myobj.celldata.keys()` to return the available data array names

            `myobj.celldata.select(name)` to make this array the active one

            `myobj.celldata.remove(name)` to remove this array
        """
        return DataArrayHelper(self, 1)

    @property
    def metadata(self):
        """
        Create and/or return a `numpy.array` associated to neither cells nor faces.
        A data array can be indexed either as a string or by an integer number.
        E.g.:  `myobj.metadata["arrayname"]`

        Usage:

            `myobj.metadata.keys()` to return the available data array names

            `myobj.metadata.select(name)` to make this array the active one

            `myobj.metadata.remove(name)` to remove this array
        """
        return DataArrayHelper(self, 2)

    def add_observer(self, event_name, func, priority=0):
        """Add a callback function that will be called when an event occurs."""
        event_name = utils.get_vtk_name_event(event_name)
        idd = self.AddObserver(event_name, func, priority)
        return idd

    def memory_address(self):
        """
        Return a unique memory address integer which may serve as the ID of the
        object, or passed to c++ code.
        """
        # https://www.linkedin.com/pulse/speedup-your-code-accessing-python-vtk-objects-from-c-pletzer/
        # https://github.com/tfmoraes/polydata_connectivity
        return int(self.GetAddressAsString("")[5:], 16)

    def memory_size(self):
        """
        Return the size in bytes of the object in memory.
        """
        return self.dataset.GetActualMemorySize()

    def modified(self):
        """Use in conjunction with ``tonumpy()`` to update any modifications to the picture array"""
        self.dataset.GetPointData().Modified()
        self.dataset.GetPointData().GetScalars().Modified()
        return self

    def box(self, scale=1, padding=0, fill=False):
        """
        Return the bounding box as a new `Mesh`.

        Arguments:
            scale : (float)
                box size can be scaled by a factor
            padding : (float, list)
                a constant padding can be added (can be a list [padx,pady,padz])

        Examples:
            - [latex.py](https://github.com/marcomusy/vedo/tree/master/examples/pyplot/latex.py)
        """
        b = self.bounds()
        if not utils.is_sequence(padding):
            padding = [padding, padding, padding]
        length, width, height = b[1] - b[0], b[3] - b[2], b[5] - b[4]
        tol = (length + width + height) / 30000  # useful for boxing 2D text
        pos = [(b[0] + b[1]) / 2, (b[3] + b[2]) / 2, (b[5] + b[4]) / 2 - tol]
        bx = vedo.shapes.Box(
            pos,
            length * scale + padding[0],
            width * scale + padding[1],
            height * scale + padding[2],
            c="gray",
        )
        try:
            pr = vtk.vtkProperty()
            pr.DeepCopy(self.property)
            bx.SetProperty(pr)
            bx.property = pr
        except (AttributeError, TypeError):
            pass
        bx.wireframe(not fill)
        bx.flat().lighting("off")
        return bx

    def bounds(self):
        """
        Get the object bounds.
        Returns a list in format `[xmin,xmax, ymin,ymax, zmin,zmax]`.
        """
        try:
            pts = self.vertices
            xmin, ymin, zmin = np.min(pts, axis=0)
            xmax, ymax, zmax = np.max(pts, axis=0)
            return (xmin, xmax, ymin, ymax, zmin, zmax)
        except (AttributeError, ValueError):
            return self.dataset.GetBounds()

    def xbounds(self, i=None):
        """Get the bounds `[xmin,xmax]`. Can specify upper or lower with i (0,1)."""
        b = self.bounds()
        if i is not None:
            return b[i]
        return (b[0], b[1])

    def ybounds(self, i=None):
        """Get the bounds `[ymin,ymax]`. Can specify upper or lower with i (0,1)."""
        b = self.bounds()
        if i == 0:
            return b[2]
        if i == 1:
            return b[3]
        return (b[2], b[3])

    def zbounds(self, i=None):
        """Get the bounds `[zmin,zmax]`. Can specify upper or lower with i (0,1)."""
        b = self.bounds()
        if i == 0:
            return b[4]
        if i == 1:
            return b[5]
        return (b[4], b[5])

    def diagonal_size(self):
        """Get the length of the diagonal of mesh bounding box."""
        b = self.bounds()
        return np.sqrt((b[1] - b[0]) ** 2 + (b[3] - b[2]) ** 2 + (b[5] - b[4]) ** 2)

    def average_size(self):
        """
        Calculate the average size of a mesh.
        This is the mean of the vertex distances from the center of mass.
        """
        coords = self.vertices
        cm = np.mean(coords, axis=0)
        if coords.shape[0] == 0:
            return 0.0
        cc = coords - cm
        return np.mean(np.linalg.norm(cc, axis=1))

    def center_of_mass(self):
        """Get the center of mass of mesh."""
        cmf = vtk.vtkCenterOfMass()
        cmf.SetInputData(self.dataset)
        cmf.Update()
        c = cmf.GetCenter()
        return np.array(c)

    def copy_data_from(self, obj):
        """Copy all data (point and cell data) from this input object"""
        self.dataset.GetPointData().PassData(obj.dataset.GetPointData())
        self.dataset.GetCellData().PassData(obj.dataset.GetCellData())
        self.pipeline = utils.OperationNode(
            f"copy_data_from\n{obj.__class__.__name__}",
            parents=[self, obj],
            shape="note",
            c="#ccc5b9",
        )
        return self

    def print(self):
        """Print information about an object."""
        utils.print_info(self)
        return self

    def inputdata(self):
        """Obsolete, use `.dataset` instead."""
        colors.printc("WARNING: 'inputdata()' is obsolete, use '.dataset' instead.", c="y")
        return self.dataset

    @property
    def npoints(self):
        """Retrieve the number of points."""
        return self.dataset.GetNumberOfPoints()

    @property
    def ncells(self):
        """Retrieve the number of cells."""
        return self.dataset.GetNumberOfCells()

    def points(self, pts=None):
        """
        Obsolete, use `self.vertices` instead.

        Set/Get the vertex coordinates of a mesh or point cloud.
        """
        if pts is None:  ### getter
            msg = (
                "WARNING: points() is deprecated, use vertices instead. E.g.:\n"
                "         mesh.points() -> mesh.vertices"
            )
            colors.printc(msg, c="y")
            return self.vertices

        else:
            msg = (
                "WARNING: points() is deprecated, use vertices instead. E.g.:\n"
                "         mesh.points([[x,y,z]]) -> mesh.vertices = [[x,y,z]]"
            )
            colors.printc(msg, c="y")

            pts = np.asarray(pts, dtype=np.float32)

            if pts.ndim == 1:
                ### getter by point index ###################
                indices = pts.astype(int)
                vpts = self.dataset.GetPoints()
                arr = utils.vtk2numpy(vpts.GetData())
                return arr[indices]  ###########

            ### setter ####################################
            if pts.shape[1] == 2:
                pts = np.c_[pts, np.zeros(pts.shape[0], dtype=np.float32)]
            arr = utils.numpy2vtk(pts, dtype=np.float32)

            vpts = self.dataset.GetPoints()
            vpts.SetData(arr)
            vpts.Modified()
            # reset mesh to identity matrix position/rotation:
            self.point_locator = None
            self.cell_locator = None
            self.actor.PokeMatrix(vtk.vtkMatrix4x4())
            self.transform = LinearTransform()
            return self

    @property
    def cell_centers(self):
        """
        Get the coordinates of the cell centers.

        Examples:
            - [delaunay2d.py](https://github.com/marcomusy/vedo/tree/master/examples/basic/delaunay2d.py)
        """
        vcen = vtk.vtkCellCenters()
        vcen.SetInputData(self.dataset)
        vcen.Update()
        return utils.vtk2numpy(vcen.GetOutput().GetPoints().GetData())

    @property
    def lines(self):
        """
        Get lines connectivity ids as a numpy array.
        Default format is `[[id0,id1], [id3,id4], ...]`

        Arguments:
            flat : (bool)
                return a 1D numpy array as e.g. [2, 10,20, 3, 10,11,12, 2, 70,80, ...]
        """
        # Get cell connettivity ids as a 1D array. The vtk format is:
        #    [nids1, id0 ... idn, niids2, id0 ... idm,  etc].
        arr1d = vtk2numpy(self.dataset.GetLines().GetData())
        i = 0
        conn = []
        n = len(arr1d)
        for _ in range(n):
            cell = [arr1d[i + k + 1] for k in range(arr1d[i])]
            conn.append(cell)
            i += arr1d[i] + 1
            if i >= n:
                break

        return conn  # cannot always make a numpy array of it!

    @property
    def lines_as_flat_array(self):
        """
        Get lines connectivity ids as a numpy array.
        Format is e.g. [2,  10,20,  3, 10,11,12,  2, 70,80, ...]
        """
        return vtk2numpy(self.dataset.GetLines().GetData())

    def mark_boundaries(self):
        """
        Mark cells and vertices of the mesh if they lie on a boundary.
        A new array called `BoundaryCells` is added to the mesh.
        """
        mb = vtk.vtkMarkBoundaryFilter()
        mb.SetInputData(self.dataset)
        mb.Update()
        self.DeepCopy(mb.GetOutput())
        self.pipeline = utils.OperationNode("mark_boundaries", parents=[self])
        return self

    def find_cells_in_bounds(self, xbounds=(), ybounds=(), zbounds=()):
        """
        Find cells that are within the specified bounds.
        """
        if len(xbounds) == 6:
            bnds = xbounds
        else:
            bnds = list(self.bounds())
            if len(xbounds) == 2:
                bnds[0] = xbounds[0]
                bnds[1] = xbounds[1]
            if len(ybounds) == 2:
                bnds[2] = ybounds[0]
                bnds[3] = ybounds[1]
            if len(zbounds) == 2:
                bnds[4] = zbounds[0]
                bnds[5] = zbounds[1]

        cellIds = vtk.vtkIdList()
        if not self.cell_locator:
            self.cell_locator = vtk.vtkCellTreeLocator()
            self.cell_locator.SetDataSet(self.dataset)
            self.cell_locator.BuildLocator()
        self.cell_locator.FindCellsWithinBounds(bnds, cellIds)
        cids = []
        for i in range(cellIds.GetNumberOfIds()):
            cid = cellIds.GetId(i)
            cids.append(cid)
        return np.array(cids)

    def find_cells_along_line(self, p0, p1, tol=0.001):
        """
        Find cells that are intersected by a line segment.
        """
        cellIds = vtk.vtkIdList()
        if not self.cell_locator:
            self.cell_locator = vtk.vtkCellTreeLocator()
            self.cell_locator.SetDataSet(self.dataset)
            self.cell_locator.BuildLocator()
        self.cell_locator.FindCellsWithinBounds(bnds, cellIds)
        self.cell_locator.FindCellsAlongLine(p0, p1, tol, cellsIds)   
        cids = []
        for i in range(cellIds.GetNumberOfIds()):
            cid = cellIds.GetId(i)
            cids.append(cid)
        return np.array(cids)

    def find_cells_along_plane(self, origin, normal, tol=0.001):
        """
        Find cells that are intersected by a plane.
        """
        cellIds = vtk.vtkIdList()
        if not self.cell_locator:
            self.cell_locator = vtk.vtkCellTreeLocator()
            self.cell_locator.SetDataSet(self.dataset)
            self.cell_locator.BuildLocator()
        self.cell_locator.FindCellsWithinBounds(bnds, cellIds)
        self.cell_locator.FindCellsAlongPlane(origin, normal, tol, cellsIds)   
        cids = []
        for i in range(cellIds.GetNumberOfIds()):
            cid = cellIds.GetId(i)
            cids.append(cid)
        return np.array(cids)

    def delete_cells_by_point_index(self, indices):
        """
        Delete a list of vertices identified by any of their vertex index.

        See also `delete_cells()`.

        Examples:
            - [delete_mesh_pts.py](https://github.com/marcomusy/vedo/tree/master/examples/basic/delete_mesh_pts.py)

                ![](https://vedo.embl.es/images/basic/deleteMeshPoints.png)
        """
        cell_ids = vtk.vtkIdList()
        self.dataset.BuildLinks()
        n = 0
        for i in np.unique(indices):
            self.dataset.GetPointCells(i, cell_ids)
            for j in range(cell_ids.GetNumberOfIds()):
                self.dataset.DeleteCell(cell_ids.GetId(j))  # flag cell
                n += 1

        self.dataset.RemoveDeletedCells()
        self.mapper.Modified()
        self.pipeline = utils.OperationNode(f"delete {n} cells\nby point index", parents=[self])
        return self

    def map_cells_to_points(self, arrays=(), move=False):
        """
        Interpolate cell data (i.e., data specified per cell or face)
        into point data (i.e., data specified at each vertex).
        The method of transformation is based on averaging the data values
        of all cells using a particular point.

        A custom list of arrays to be mapped can be passed in input.

        Set `move=True` to delete the original `celldata` array.
        """
        c2p = vtk.vtkCellDataToPointData()
        c2p.SetInputData(self.dataset)
        if not move:
            c2p.PassCellDataOn()
        if arrays:
            c2p.ClearCellDataArrays()
            c2p.ProcessAllArraysOff()
            for arr in arrays:
                c2p.AddCellDataArray(arr)
        else:
            c2p.ProcessAllArraysOn()
        c2p.Update()
        self.mapper.SetScalarModeToUsePointData()
        self._update(c2p.GetOutput(), reset_locators=False)
        self.pipeline = utils.OperationNode("map cell\nto point data", parents=[self])
        return self

    @property
    def vertices(self):
        """Return the vertices (points) coordinates."""
        varr = self.dataset.GetPoints().GetData()
        narr = utils.vtk2numpy(varr)
        return narr

    # setter
    @vertices.setter
    def vertices(self, pts):
        """Set vertices (points) coordinates."""
        arr = utils.numpy2vtk(pts, dtype=np.float32)
        vpts = self.dataset.GetPoints()
        vpts.SetData(arr)
        vpts.Modified()
        # reset mesh to identity matrix position/rotation:
        self.point_locator = None
        self.cell_locator = None
        self.line_locator = None
        self.actor.PokeMatrix(vtk.vtkMatrix4x4())
        self.transform = LinearTransform()
        # BUG
        # from vedo import *
        # plt = Plotter(interactive=False, axes=7)
        # s = Disc(res=(8,120)).linewidth(0.1)
        # print([s.dataset.GetPoints().GetData()])
        # # plt.show(s)  # depends if I show it or not..
        # # plt.renderer.AddActor(s.actor)
        # print([s.dataset.GetPoints().GetData()])
        # for i in progressbar(100):
        #     s.vertices[:,2] = sin(i/10.*s.vertices[:,0])/5 # move vertices in z
        # show(s, interactive=1)
        # exit()
        return self

    @property
    def cells(self):
        """
        Get the cells connectivity ids as a numpy array.

        The output format is: `[[id0 ... idn], [id0 ... idm],  etc]`.
        """
        arr1d = utils.vtk2numpy(self.dataset.GetCells().GetData())

        # Get cell connettivity ids as a 1D array. vtk format is:
        # [nids1, id0 ... idn, niids2, id0 ... idm,  etc].
        i = 0
        conn = []
        n = len(arr1d)
        if n:
            while True:
                cell = [arr1d[i + k] for k in range(1, arr1d[i] + 1)]
                conn.append(cell)
                i += arr1d[i] + 1
                if i >= n:
                    break
        return conn

    def map_points_to_cells(self, arrays=(), move=False):
        """
        Interpolate point data (i.e., data specified per point or vertex)
        into cell data (i.e., data specified per cell).
        The method of transformation is based on averaging the data values
        of all points defining a particular cell.

        A custom list of arrays to be mapped can be passed in input.

        Set `move=True` to delete the original `pointdata` array.

        Examples:
            - [mesh_map2cell.py](https://github.com/marcomusy/vedo/tree/master/examples/basic/mesh_map2cell.py)
        """
        p2c = vtk.vtkPointDataToCellData()
        p2c.SetInputData(self.dataset)
        if not move:
            p2c.PassPointDataOn()
        if arrays:
            p2c.ClearPointDataArrays()
            p2c.ProcessAllArraysOff()
            for arr in arrays:
                p2c.AddPointDataArray(arr)
        else:
            p2c.ProcessAllArraysOn()
        p2c.Update()
        self.mapper.SetScalarModeToUseCellData()
        self._update(p2c.GetOutput(), reset_locators=False)
        self.pipeline = utils.OperationNode("map point\nto cell data", parents=[self])
        return self

    def resample_data_from(self, source, tol=None, categorical=False):
        """
        Resample point and cell data from another dataset.
        The output has the same structure but its point data have
        the resampled values from target.

        Use `tol` to set the tolerance used to compute whether
        a point in the source is in a cell of the current object.
        Points without resampled values, and their cells, are marked as blank.
        If the data is categorical, then the resulting data will be determined
        by a nearest neighbor interpolation scheme.

        Example:
        ```python
        from vedo import *
        m1 = Mesh(dataurl+'bunny.obj')#.add_gaussian_noise(0.1)
        pts = m1.vertices
        ces = m1.cell_centers
        m1.pointdata["xvalues"] = np.power(pts[:,0], 3)
        m1.celldata["yvalues"]  = np.power(ces[:,1], 3)
        m2 = Mesh(dataurl+'bunny.obj')
        m2.resample_arrays_from(m1)
        # print(m2.pointdata["xvalues"])
        show(m1, m2 , N=2, axes=1)
        ```
        """
        rs = vtk.vtkResampleWithDataSet()
        rs.SetInputData(self.dataset)
        rs.SetSourceData(source.dataset)

        rs.SetPassPointArrays(True)
        rs.SetPassCellArrays(True)
        rs.SetPassFieldArrays(True)
        rs.SetCategoricalData(categorical)

        rs.SetComputeTolerance(True)
        if tol:
            rs.SetComputeTolerance(False)
            rs.SetTolerance(tol)
        rs.Update()
        self._update(rs.GetOutput(), reset_locators=False)
        self.pipeline = utils.OperationNode(
            f"resample_data_from\n{source.__class__.__name__}", parents=[self, source]
        )
        return self

    def interpolate_data_from(
        self,
        source,
        radius=None,
        n=None,
        kernel="shepard",
        exclude=("Normals",),
        on="points",
        null_strategy=1,
        null_value=0,
    ):
        """
        Interpolate over source to port its data onto the current object using various kernels.

        If n (number of closest points to use) is set then radius value is ignored.

        Arguments:
            kernel : (str)
                available kernels are [shepard, gaussian, linear, voronoi]
            null_strategy : (int)
                specify a strategy to use when encountering a "null" point
                during the interpolation process. Null points occur when the local neighborhood
                (of nearby points to interpolate from) is empty.

                - Case 0: an output array is created that marks points
                  as being valid (=1) or null (invalid =0), and the null_value is set as well
                - Case 1: the output data value(s) are set to the provided null_value
                - Case 2: simply use the closest point to perform the interpolation.
            null_value : (float)
                see above.

        Examples:
            - [interpolate_scalar3.py](https://github.com/marcomusy/vedo/tree/master/examples/advanced/interpolate_scalar3.py)

                ![](https://vedo.embl.es/images/advanced/interpolateMeshArray.png)
        """
        if radius is None and not n:
            vedo.logger.error("in interpolate_data_from(): please set either radius or n")
            raise RuntimeError

        if on == "points":
            points = source.dataset
        elif on == "cells":
            c2p = vtk.vtkCellDataToPointData()
            # poly2 = vtk.vtkPolyData()
            # poly2.ShallowCopy(source.dataset)
            c2p.SetInputData(source.dataset)
            c2p.Update()
            points = c2p.GetOutput()
        else:
            vedo.logger.error("in interpolate_data_from(), on must be on points or cells")
            raise RuntimeError()

        locator = vtk.vtkPointLocator()
        locator.SetDataSet(points)
        locator.BuildLocator()

        if kernel.lower() == "shepard":
            kern = vtk.vtkShepardKernel()
            kern.SetPowerParameter(2)
        elif kernel.lower() == "gaussian":
            kern = vtk.vtkGaussianKernel()
            kern.SetSharpness(2)
        elif kernel.lower() == "linear":
            kern = vtk.vtkLinearKernel()
        elif kernel.lower() == "voronoi":
            kern = vtk.vtkProbabilisticVoronoiKernel()
        else:
            vedo.logger.error("available kernels are: [shepard, gaussian, linear, voronoi]")
            raise RuntimeError()

        if n:
            kern.SetNumberOfPoints(n)
            kern.SetKernelFootprintToNClosest()
        else:
            kern.SetRadius(radius)
            kern.SetKernelFootprintToRadius()

        interpolator = vtk.vtkPointInterpolator()
        interpolator.SetInputData(self.dataset)
        interpolator.SetSourceData(points)
        interpolator.SetKernel(kern)
        interpolator.SetLocator(locator)
        interpolator.PassFieldArraysOff()
        interpolator.SetNullPointsStrategy(null_strategy)
        interpolator.SetNullValue(null_value)
        interpolator.SetValidPointsMaskArrayName("ValidPointMask")
        for ex in exclude:
            interpolator.AddExcludedArray(ex)
        interpolator.Update()

        if on == "cells":
            p2c = vtk.vtkPointDataToCellData()
            p2c.SetInputData(interpolator.GetOutput())
            p2c.Update()
            cpoly = p2c.GetOutput()
        else:
            cpoly = interpolator.GetOutput()

        self._update(cpoly, reset_locators=False)

        self.pipeline = utils.OperationNode("interpolate_data_from", parents=[self, source])
        return self

    def add_ids(self):
        """Generate point and cell ids arrays."""
        ids = vtk.vtkIdFilter()
        ids.SetInputData(self.dataset)
        ids.PointIdsOn()
        ids.CellIdsOn()
        ids.FieldDataOff()
        ids.SetPointIdsArrayName("PointID")
        ids.SetCellIdsArrayName("CellID")
        ids.Update()
        self._update(ids.GetOutput(), reset_locators=False)
        self.pipeline = utils.OperationNode("add_ids", parents=[self])
        return self

    def gradient(self, input_array=None, on="points", fast=False):
        """
        Compute and return the gradiend of the active scalar field as a numpy array.

        Arguments:
            input_array : (str)
                array of the scalars to compute the gradient,
                if None the current active array is selected
            on : (str)
                compute either on 'points' or 'cells' data
            fast : (bool)
                if True, will use a less accurate algorithm
                that performs fewer derivative calculations (and is therefore faster).

        Examples:
            - [isolines.py](https://github.com/marcomusy/vedo/tree/master/examples/advanced/isolines.py)

            ![](https://user-images.githubusercontent.com/32848391/72433087-f00a8780-3798-11ea-9778-991f0abeca70.png)
        """
        gra = vtk.vtkGradientFilter()
        if on.startswith("p"):
            varr = self.dataset.GetPointData()
            tp = vtk.vtkDataObject.FIELD_ASSOCIATION_POINTS
        elif on.startswith("c"):
            varr = self.dataset.GetCellData()
            tp = vtk.vtkDataObject.FIELD_ASSOCIATION_CELLS
        else:
            vedo.logger.error(f"in gradient: unknown option {on}")
            raise RuntimeError

        if input_array is None:
            if varr.GetScalars():
                input_array = varr.GetScalars().GetName()
            else:
                vedo.logger.error(f"in gradient: no scalars found for {on}")
                raise RuntimeError

        gra.SetInputData(self.dataset)
        gra.SetInputScalars(tp, input_array)
        gra.SetResultArrayName("Gradient")
        gra.SetFasterApproximation(fast)
        gra.ComputeDivergenceOff()
        gra.ComputeVorticityOff()
        gra.ComputeGradientOn()
        gra.Update()
        if on.startswith("p"):
            gvecs = utils.vtk2numpy(gra.GetOutput().GetPointData().GetArray("Gradient"))
        else:
            gvecs = utils.vtk2numpy(gra.GetOutput().GetCellData().GetArray("Gradient"))
        return gvecs

    def divergence(self, array_name=None, on="points", fast=False):
        """
        Compute and return the divergence of a vector field as a numpy array.

        Arguments:
            array_name : (str)
                name of the array of vectors to compute the divergence,
                if None the current active array is selected
            on : (str)
                compute either on 'points' or 'cells' data
            fast : (bool)
                if True, will use a less accurate algorithm
                that performs fewer derivative calculations (and is therefore faster).
        """
        div = vtk.vtkGradientFilter()
        if on.startswith("p"):
            varr = self.dataset.GetPointData()
            tp = vtk.vtkDataObject.FIELD_ASSOCIATION_POINTS
        elif on.startswith("c"):
            varr = self.dataset.GetCellData()
            tp = vtk.vtkDataObject.FIELD_ASSOCIATION_CELLS
        else:
            vedo.logger.error(f"in divergence(): unknown option {on}")
            raise RuntimeError

        if array_name is None:
            if varr.GetVectors():
                array_name = varr.GetVectors().GetName()
            else:
                vedo.logger.error(f"in divergence(): no vectors found for {on}")
                raise RuntimeError

        div.SetInputData(self.dataset)
        div.SetInputScalars(tp, array_name)
        div.ComputeDivergenceOn()
        div.ComputeGradientOff()
        div.ComputeVorticityOff()
        div.SetDivergenceArrayName("Divergence")
        div.SetFasterApproximation(fast)
        div.Update()
        if on.startswith("p"):
            dvecs = utils.vtk2numpy(div.GetOutput().GetPointData().GetArray("Divergence"))
        else:
            dvecs = utils.vtk2numpy(div.GetOutput().GetCellData().GetArray("Divergence"))
        return dvecs

    def vorticity(self, array_name=None, on="points", fast=False):
        """
        Compute and return the vorticity of a vector field as a numpy array.

        Arguments:
            array_name : (str)
                name of the array to compute the vorticity,
                if None the current active array is selected
            on : (str)
                compute either on 'points' or 'cells' data
            fast : (bool)
                if True, will use a less accurate algorithm
                that performs fewer derivative calculations (and is therefore faster).
        """
        vort = vtk.vtkGradientFilter()
        if on.startswith("p"):
            varr = self.dataset.GetPointData()
            tp = vtk.vtkDataObject.FIELD_ASSOCIATION_POINTS
        elif on.startswith("c"):
            varr = self.dataset.GetCellData()
            tp = vtk.vtkDataObject.FIELD_ASSOCIATION_CELLS
        else:
            vedo.logger.error(f"in vorticity(): unknown option {on}")
            raise RuntimeError

        if array_name is None:
            if varr.GetVectors():
                array_name = varr.GetVectors().GetName()
            else:
                vedo.logger.error(f"in vorticity(): no vectors found for {on}")
                raise RuntimeError

        vort.SetInputData(self.dataset)
        vort.SetInputScalars(tp, array_name)
        vort.ComputeDivergenceOff()
        vort.ComputeGradientOff()
        vort.ComputeVorticityOn()
        vort.SetVorticityArrayName("Vorticity")
        vort.SetFasterApproximation(fast)
        vort.Update()
        if on.startswith("p"):
            vvecs = utils.vtk2numpy(vort.GetOutput().GetPointData().GetArray("Vorticity"))
        else:
            vvecs = utils.vtk2numpy(vort.GetOutput().GetCellData().GetArray("Vorticity"))
        return vvecs

    def compute_cell_size(self):
        """Add to this mesh a cell data array containing the areas of the polygonal faces"""
        csf = vtk.vtkCellSizeFilter()
        csf.SetInputData(self.dataset)
        csf.SetComputeArea(1)
        csf.SetComputeVolume(1)
        csf.SetComputeLength(1)
        csf.SetComputeVertexCount(0)
        csf.SetAreaArrayName("Area")
        csf.SetVolumeArrayName("Volume")
        csf.SetLengthArrayName("Length")
        csf.Update()
        self._update(csf.GetOutput(), reset_locators=False)
        return self

    def write(self, filename, binary=True):
        """Write object to file."""
        out = vedo.file_io.write(self, filename, binary)
        out.pipeline = utils.OperationNode(
            "write", parents=[self], comment=filename[:15], shape="folder", c="#8a817c"
        )
        return out

    def tomesh(self, fill=True, shrink=1.0):
        """
        Build a polygonal Mesh from the current object.

        If `fill=True`, the interior faces of all the cells are created.
        (setting a `shrink` value slightly smaller than the default 1.0
        can avoid flickering due to internal adjacent faces).

        If `fill=False`, only the boundary faces will be generated.
        """
        gf = vtk.vtkGeometryFilter()
        if fill:
            sf = vtk.vtkShrinkFilter()
            sf.SetInputData(self.dataset)
            sf.SetShrinkFactor(shrink)
            sf.Update()
            gf.SetInputData(sf.GetOutput())
            gf.Update()
            poly = gf.GetOutput()
            if shrink == 1.0:
                cleanPolyData = vtk.vtkCleanPolyData()
                cleanPolyData.PointMergingOn()
                cleanPolyData.ConvertLinesToPointsOn()
                cleanPolyData.ConvertPolysToLinesOn()
                cleanPolyData.ConvertStripsToPolysOn()
                cleanPolyData.SetInputData(poly)
                cleanPolyData.Update()
                poly = cleanPolyData.GetOutput()
        else:
            gf.SetInputData(self.dataset)
            gf.Update()
            poly = gf.GetOutput()

        msh = vedo.mesh.Mesh(poly).flat()
        msh.scalarbar = self.scalarbar
        lut = utils.ctf2lut(self)
        if lut:
            msh.mapper.SetLookupTable(lut)

        msh.pipeline = utils.OperationNode(
            "tomesh", parents=[self], comment=f"fill={fill}", c="#9e2a2b:#e9c46a"
        )
        return msh

    def tomesh(self, bounds=()):
        """Extract boundary geometry from dataset (or convert data to polygonal type)."""
        geo = vtk.vtkGeometryFilter()
        geo.SetInputData(self.dataset)
        geo.SetPassThroughCellIds(1)
        geo.SetPassThroughPointIds(1)
        geo.SetOriginalCellIdsName("OriginalCellIds")
        geo.SetOriginalPointIdsName("OriginalPointIds")
        geo.SetNonlinearSubdivisionLevel(1)
        geo.MergingOff()
        if bounds:
            geo.SetExtent(bounds)
            geo.ExtentClippingOn()
        geo.Update()
        msh = vedo.mesh.Mesh(geo.GetOutput())
        msh.pipeline = utils.OperationNode("tomesh", parents=[self], c="#9e2a2b")
        return msh

    def shrink(self, fraction=0.8):
        """
        Shrink the individual cells to improve visibility.

        ![](https://vedo.embl.es/images/feats/shrink_hex.png)
        """
        sf = vtk.vtkShrinkFilter()
        sf.SetInputData(self.dataset)
        sf.SetShrinkFactor(fraction)
        sf.Update()
        self._update(sf.GetOutput())
        self.pipeline = utils.OperationNode(
            "shrink", comment=f"by {fraction}", parents=[self], c="#9e2a2b"
        )
        return self


###############################################################################
class PointAlgorithms(CommonAlgorithms):
    """Methods for point clouds."""

    def apply_transform(self, LT, concatenate=True, deep_copy=True):
        """
        Apply a linear or non-linear transformation to the mesh polygonal data.
            ```python
            from vedo import Cube, show
            c1 = Cube().rotate_z(5).x(2).y(1)
            print("cube1 position", c1.pos())
            T = c1.get_transform()  # rotate by 5 degrees, sum 2 to x and 1 to y
            c2 = Cube().c('r4')
            c2.apply_transform(T)   # ignore previous movements
            c2.apply_transform(T, concatenate=True)
            c2.apply_transform(T, concatenate=True)
            print("cube2 position", c2.pos())
            show(c1, c2, axes=1).close()
            ```
            ![](https://vedo.embl.es/images/feats/apply_transform.png)
        """
        if self.dataset.GetNumberOfPoints() == 0:
            return self

        if isinstance(LT, LinearTransform):
            tr = LT.T
            if LT.is_identity():
                return self
            if concatenate:
                self.transform.concatenate(LT)
        elif isinstance(LT, (vtk.vtkMatrix4x4, vtk.vtkLinearTransform, np.ndarray)):
            LT = LinearTransform(LT)
            if LT.is_identity():
                return self
            tr = LT.T
            if concatenate:
                self.transform.concatenate(LT)
        elif isinstance(LT, (vtk.vtkThinPlateSplineTransform)):
            tr = LT
            # cannot concatenate here

        tp = vtk.vtkTransformPolyDataFilter()
        tp.SetTransform(tr)
        tp.SetInputData(self.dataset)
        tp.Update()
        out = tp.GetOutput()

        if deep_copy:
            self.dataset.DeepCopy(out)
        else:
            self.dataset.ShallowCopy(out)

        # reset the locators
        self.point_locator = None
        self.cell_locator = None
        self.line_locator = None
        return self

    def pos(self, x=None, y=None, z=None):
        """Set/Get object position."""
        if x is None:  # get functionality
            return self.transform.position

        if z is None and y is None:  # assume x is of the form (x,y,z)
            if len(x) == 3:
                x, y, z = x
            else:
                x, y = x
                z = 0
        elif z is None:  # assume x,y is of the form x, y
            z = 0

        q = self.transform.position
        LT = LinearTransform()
        LT.translate([x, y, z] - q)
        return self.apply_transform(LT)

    def shift(self, dx=0, dy=0, dz=0):
        """Add a vector to the current object position."""
        if utils.is_sequence(dx):
            utils.make3d(dx)
            dx, dy, dz = dx
        LT = LinearTransform().translate([dx, dy, dz])
        return self.apply_transform(LT)

    def x(self, val=None):
        """Set/Get object position along x axis."""
        p = self.transform.position
        if val is None:
            return p[0]
        self.pos(val, p[1], p[2])
        return self

    def y(self, val=None):
        """Set/Get object position along y axis."""
        p = self.transform.position
        if val is None:
            return p[1]
        self.pos(p[0], val, p[2])
        return self

    def z(self, val=None):
        """Set/Get object position along z axis."""
        p = self.transform.position
        if val is None:
            return p[2]
        self.pos(p[0], p[1], val)
        return self

    def rotate(self, angle, axis=(1, 0, 0), point=(0, 0, 0), rad=False):
        """
        Rotate around an arbitrary `axis` passing through `point`.

        Example:
            ```python
            from vedo import *
            c1 = Cube()
            c2 = c1.clone().c('violet').alpha(0.5) # copy of c1
            v = vector(0.2,1,0)
            p = vector(1,0,0)  # axis passes through this point
            c2.rotate(90, axis=v, point=p)
            l = Line(-v+p, v+p).lw(3).c('red')
            show(c1, l, c2, axes=1).close()
            ```
            ![](https://vedo.embl.es/images/feats/rotate_axis.png)
        """
        # self.rotate(angle, axis, point, rad)
        LT = LinearTransform()
        LT.rotate(angle, axis, point, rad)
        return self.apply_transform(LT)

    def rotate_x(self, angle, rad=False, around=None):
        """
        Rotate around x-axis. If angle is in radians set `rad=True`.

        Use `around` to define a pivoting point.
        """
        LT = LinearTransform().rotate_x(angle, rad, around)
        return self.apply_transform(LT)

    def rotate_y(self, angle, rad=False, around=None):
        """
        Rotate around y-axis. If angle is in radians set `rad=True`.

        Use `around` to define a pivoting point.
        """
        LT = LinearTransform().rotate_y(angle, rad, around)
        return self.apply_transform(LT)

    def rotate_z(self, angle, rad=False, around=None):
        """
        Rotate around z-axis. If angle is in radians set `rad=True`.

        Use `around` to define a pivoting point.
        """
        LT = LinearTransform().rotate_z(angle, rad, around)
        return self.apply_transform(LT)

    def reorient(self, newaxis, initaxis=None, rotation=0, rad=False, xyplane=True):
        """
        Reorient the object to point to a new direction from an initial one.
        If `initaxis` is None, the object will be assumed in its "default" orientation.
        If `xyplane` is True, the object will be rotated to lie on the xy plane.

        Use `rotation` to first rotate the object around its `initaxis`.
        """
        if initaxis is None:
            initaxis = np.asarray(self.top) - self.base

        q = self.transform.position
        LT = LinearTransform()
        LT.reorient(newaxis, initaxis, q, rotation, rad, xyplane)
        return self.apply_transform(LT)

    def scale(self, s=None, reset=False, origin=True):
        """
        Set/get object's scaling factor.

        Arguments:
            s : (list, float)
                scaling factor(s).
            reset : (bool)
                if True previous scaling factors are ignored.
            origin : (bool)
                if True scaling is applied with respect to object's position,
                otherwise is applied respect to (0,0,0).

        Note:
            use `s=(sx,sy,sz)` to scale differently in the three coordinates.
        """
        if s is None:
            return np.array(self.transform.T.GetScale())

        if not utils.is_sequence(s):
            s = [s, s, s]

        LT = LinearTransform()
        if reset:
            old_s = np.array(self.transform.T.GetScale())
            LT.scale(s / old_s)
        else:
            if origin is True:
                LT.scale(s, origin=self.transform.position)
            elif origin is False:
                LT.scale(s, origin=False)
            else:
                LT.scale(s, origin=origin)

        return self.apply_transform(LT)


###############################################################################
class VolumeAlgorithms(CommonAlgorithms):
    """Methods for Volume objects."""

    def isosurface(self, value=None, flying_edges=True):
        """
        Return an `Mesh` isosurface extracted from the `Volume` object.

        Set `value` as single float or list of values to draw the isosurface(s).
        Use flying_edges for faster results (but sometimes can interfere with `smooth()`).

        Examples:
            - [isosurfaces.py](https://github.com/marcomusy/vedo/tree/master/examples/volumetric/isosurfaces.py)

                ![](https://vedo.embl.es/images/volumetric/isosurfaces.png)
        """
        scrange = self.dataset.GetScalarRange()

        if flying_edges:
            cf = vtk.vtkFlyingEdges3D()
            cf.InterpolateAttributesOn()
        else:
            cf = vtk.vtkContourFilter()
            cf.UseScalarTreeOn()

        cf.SetInputData(self.dataset)
        cf.ComputeNormalsOn()

        if utils.is_sequence(value):
            cf.SetNumberOfContours(len(value))
            for i, t in enumerate(value):
                cf.SetValue(i, t)
        else:
            if value is None:
                value = (2 * scrange[0] + scrange[1]) / 3.0
                # print("automatic isosurface value =", value)
            cf.SetValue(0, value)

        cf.Update()
        poly = cf.GetOutput()

        out = vedo.mesh.Mesh(poly, c=None).phong()
        out.mapper.SetScalarRange(scrange[0], scrange[1])

        out.pipeline = utils.OperationNode(
            "isosurface",
            parents=[self],
            comment=f"#pts {out.dataset.GetNumberOfPoints()}",
            c="#4cc9f0:#e9c46a",
        )
        return out

    def legosurface(
        self,
        vmin=None,
        vmax=None,
        invert=False,
        boundary=False,
        array_name="input_scalars",
    ):
        """
        Represent an object - typically a `Volume` - as lego blocks (voxels).
        By default colors correspond to the volume's scalar.
        Returns an `Mesh` object.

        Arguments:
            vmin : (float)
                the lower threshold, voxels below this value are not shown.
            vmax : (float)
                the upper threshold, voxels above this value are not shown.
            boundary : (bool)
                controls whether to include cells that are partially inside
            array_name : (int, str)
                name or index of the scalar array to be considered

        Examples:
            - [legosurface.py](https://github.com/marcomusy/vedo/tree/master/examples/volumetric/legosurface.py)

                ![](https://vedo.embl.es/images/volumetric/56820682-da40e500-684c-11e9-8ea3-91cbcba24b3a.png)
        """
        imp_dataset = vtk.vtkImplicitDataSet()
        imp_dataset.SetDataSet(self.dataset)
        window = vtk.vtkImplicitWindowFunction()
        window.SetImplicitFunction(imp_dataset)

        srng = list(self.dataset.GetScalarRange())
        if vmin is not None:
            srng[0] = vmin
        if vmax is not None:
            srng[1] = vmax
        tol = 0.00001 * (srng[1] - srng[0])
        srng[0] -= tol
        srng[1] += tol
        window.SetWindowRange(srng)

        extract = vtk.vtkExtractGeometry()
        extract.SetInputData(self.dataset)
        extract.SetImplicitFunction(window)
        extract.SetExtractInside(invert)
        extract.SetExtractBoundaryCells(boundary)
        extract.Update()

        gf = vtk.vtkGeometryFilter()
        gf.SetInputData(extract.GetOutput())
        gf.Update()

        m = vedo.mesh.Mesh(gf.GetOutput()).lw(0.1).flat()
        m.map_points_to_cells()
        m.celldata.select(array_name)

        m.pipeline = utils.OperationNode(
            "legosurface",
            parents=[self],
            comment=f"array: {array_name}",
            c="#4cc9f0:#e9c46a",
        )
        return m

    def cut_with_plane(self, origin=(0, 0, 0), normal="x"):
        """
        Cut the object with the plane defined by a point and a normal.

        Arguments:
            origin : (list)
                the cutting plane goes through this point
            normal : (list, str)
                normal vector to the cutting plane
        """
        # if isinstance(self, vedo.Volume):
        #     raise RuntimeError("cut_with_plane() is not applicable to Volume objects.")

        strn = str(normal)
        if strn   ==  "x": normal = (1, 0, 0)
        elif strn ==  "y": normal = (0, 1, 0)
        elif strn ==  "z": normal = (0, 0, 1)
        elif strn == "-x": normal = (-1, 0, 0)
        elif strn == "-y": normal = (0, -1, 0)
        elif strn == "-z": normal = (0, 0, -1)
        plane = vtk.vtkPlane()
        plane.SetOrigin(origin)
        plane.SetNormal(normal)
        clipper = vtk.vtkClipDataSet()
        clipper.SetInputData(self.dataset)
        clipper.SetClipFunction(plane)
        clipper.GenerateClipScalarsOff()
        clipper.GenerateClippedOutputOff()
        clipper.SetValue(0)
        clipper.Update()
        cout = clipper.GetOutput()

        if isinstance(cout, vtk.vtkUnstructuredGrid):
            ug = vedo.UGrid(cout)
            if isinstance(self, vedo.UGrid):
                self._update(cout)
                self.pipeline = utils.OperationNode("cut_with_plane", parents=[self], c="#9e2a2b")
                return self
            ug.pipeline = utils.OperationNode("cut_with_plane", parents=[self], c="#9e2a2b")
            return ug

        else:
            self._update(cout)
            self.pipeline = utils.OperationNode("cut_with_plane", parents=[self], c="#9e2a2b")
            return self

    def cut_with_box(self, box):
        """
        Cut the grid with the specified bounding box.

        Parameter box has format [xmin, xmax, ymin, ymax, zmin, zmax].
        If an object is passed, its bounding box are used.

        Example:
            ```python
            from vedo import *
            tetmesh = TetMesh(dataurl+'limb_ugrid.vtk')
            tetmesh.color('rainbow')
            cu = Cube(side=500).x(500) # any Mesh works
            tetmesh.cut_with_box(cu).show(axes=1)
            ```
            ![](https://vedo.embl.es/images/feats/tet_cut_box.png)
        """
        # if isinstance(self, vedo.Volume):
        #     raise RuntimeError("cut_with_box() is not applicable to Volume objects.")

        bc = vtk.vtkBoxClipDataSet()
        bc.SetInputData(self.dataset)
        if isinstance(box, vtk.vtkProp):
            boxb = box.GetBounds()
        else:
            boxb = box
        bc.SetBoxClip(*boxb)
        bc.Update()
        cout = bc.GetOutput()

        if isinstance(cout, vtk.vtkUnstructuredGrid):
            ug = vedo.UGrid(cout)
            if isinstance(self, vedo.UGrid):
                self._update(cout)
                self.pipeline = utils.OperationNode("cut_with_box", parents=[self], c="#9e2a2b")
                return self
            ug.pipeline = utils.OperationNode("cut_with_box", parents=[self], c="#9e2a2b")
            return ug

        else:
            self._update(cout)
            self.pipeline = utils.OperationNode("cut_with_box", parents=[self], c="#9e2a2b")
            return self

    def cut_with_mesh(self, mesh, invert=False, whole_cells=False, only_boundary=False):
        """
        Cut a UGrid or TetMesh with a Mesh.

        Use `invert` to return cut off part of the input object.
        """
        # if isinstance(self, vedo.Volume):
        #     raise RuntimeError("cut_with_mesh() is not applicable to Volume objects.")

        ug = self

        ippd = vtk.vtkImplicitPolyDataDistance()
        ippd.SetInput(mesh)

        if whole_cells or only_boundary:
            clipper = vtk.vtkExtractGeometry()
            clipper.SetInputData(ug)
            clipper.SetImplicitFunction(ippd)
            clipper.SetExtractInside(not invert)
            clipper.SetExtractBoundaryCells(False)
            if only_boundary:
                clipper.SetExtractBoundaryCells(True)
                clipper.SetExtractOnlyBoundaryCells(True)
        else:
            signedDistances = vtk.vtkFloatArray()
            signedDistances.SetNumberOfComponents(1)
            signedDistances.SetName("SignedDistances")
            for pointId in range(ug.GetNumberOfPoints()):
                p = ug.GetPoint(pointId)
                signedDistance = ippd.EvaluateFunction(p)
                signedDistances.InsertNextValue(signedDistance)
            ug.GetPointData().AddArray(signedDistances)
            ug.GetPointData().SetActiveScalars("SignedDistances")
            clipper = vtk.vtkClipDataSet()
            clipper.SetInputData(ug)
            clipper.SetInsideOut(not invert)
            clipper.SetValue(0.0)

        clipper.Update()
        cout = clipper.GetOutput()

        # if ug.GetCellData().GetScalars():  # not working
        #     scalname = ug.GetCellData().GetScalars().GetName()
        #     if scalname:  # not working
        #         if self.useCells:
        #             self.celldata.select(scalname)
        #         else:
        #             self.pointdata.select(scalname)
        # self._update(cout)
        # self.pipeline = utils.OperationNode("cut_with_mesh", parents=[self, mesh], c="#9e2a2b")
        # return self

        if isinstance(cout, vtk.vtkUnstructuredGrid):
            ug = vedo.UGrid(cout)
            if isinstance(self, vedo.UGrid):
                self._update(cout)
                self.pipeline = utils.OperationNode("cut_with_mesh", parents=[self], c="#9e2a2b")
                return self
            ug.pipeline = utils.OperationNode("cut_with_mesh", parents=[self], c="#9e2a2b")
            return ug

        else:
            self._update(cout)
            self.pipeline = utils.OperationNode("cut_with_mesh", parents=[self], c="#9e2a2b")
            return self

    def extract_cells_on_plane(self, origin, normal):
        """
        Extract cells that are lying of the specified surface.
        """
        bf = vtk.vtk3DLinearGridCrinkleExtractor()
        bf.SetInputData(self.dataset)
        bf.CopyPointDataOn()
        bf.CopyCellDataOn()
        bf.RemoveUnusedPointsOff()

        plane = vtk.vtkPlane()
        plane.SetOrigin(origin)
        plane.SetNormal(normal)
        bf.SetImplicitFunction(plane)
        bf.Update()

        self._update(bf.GetOutput(), reset_locators=False)
        self.pipeline = utils.OperationNode(
            "extract_cells_on_plane",
            parents=[self],
            comment=f"#cells {self.dataset.GetNumberOfCells()}",
            c="#9e2a2b",
        )
        return self

    def extract_cells_on_sphere(self, center, radius):
        """
        Extract cells that are lying of the specified surface.
        """
        bf = vtk.vtk3DLinearGridCrinkleExtractor()
        bf.SetInputData(self.dataset)
        bf.CopyPointDataOn()
        bf.CopyCellDataOn()
        bf.RemoveUnusedPointsOff()

        sph = vtk.vtkSphere()
        sph.SetRadius(radius)
        sph.SetCenter(center)
        bf.SetImplicitFunction(sph)
        bf.Update()

        self._update(bf.GetOutput())
        self.pipeline = utils.OperationNode(
            "extract_cells_on_sphere",
            parents=[self],
            comment=f"#cells {self.dataset.GetNumberOfCells()}",
            c="#9e2a2b",
        )
        return self

    def extract_cells_on_cylinder(self, center, axis, radius):
        """
        Extract cells that are lying of the specified surface.
        """
        bf = vtk.vtk3DLinearGridCrinkleExtractor()
        bf.SetInputData(self.dataset)
        bf.CopyPointDataOn()
        bf.CopyCellDataOn()
        bf.RemoveUnusedPointsOff()

        cyl = vtk.vtkCylinder()
        cyl.SetRadius(radius)
        cyl.SetCenter(center)
        cyl.SetAxis(axis)
        bf.SetImplicitFunction(cyl)
        bf.Update()

        self.pipeline = utils.OperationNode(
            "extract_cells_on_cylinder",
            parents=[self],
            comment=f"#cells {self.dataset.GetNumberOfCells()}",
            c="#9e2a2b",
        )
        self._update(bf.GetOutput())
        return self

    def clean(self):
        """
        Cleanup unused points and empty cells
        """
        cl = vtk.vtkStaticCleanUnstructuredGrid()
        cl.SetInputData(self.dataset)
        cl.RemoveUnusedPointsOn()
        cl.ProduceMergeMapOff()
        cl.AveragePointDataOff()
        cl.Update()

        self._update(cl.GetOutput())
        self.pipeline = utils.OperationNode(
            "clean",
            parents=[self],
            comment=f"#cells {self.dataset.GetNumberOfCells()}",
            c="#9e2a2b",
        )
        return self

    def find_cell(self, p):
        """Locate the cell that contains a point and return the cell ID."""
        cell = vtk.vtkTetra()
        cellId = vtk.mutable(0)
        tol2 = vtk.mutable(0)
        subId = vtk.mutable(0)
        pcoords = [0, 0, 0]
        weights = [0, 0, 0]
        cid = self.FindCell(p, cell, cellId, tol2, subId, pcoords, weights)
        return cid

    def extract_cells_by_id(self, idlist, use_point_ids=False):
        """Return a new UGrid composed of the specified subset of indices."""
        selectionNode = vtk.vtkSelectionNode()
        if use_point_ids:
            selectionNode.SetFieldType(vtk.vtkSelectionNode.POINT)
            contcells = vtk.vtkSelectionNode.CONTAINING_CELLS()
            selectionNode.GetProperties().Set(contcells, 1)
        else:
            selectionNode.SetFieldType(vtk.vtkSelectionNode.CELL)
        selectionNode.SetContentType(vtk.vtkSelectionNode.INDICES)
        vidlist = utils.numpy2vtk(idlist, dtype="id")
        selectionNode.SetSelectionList(vidlist)
        selection = vtk.vtkSelection()
        selection.AddNode(selectionNode)
        es = vtk.vtkExtractSelection()
        es.SetInputData(0, self)
        es.SetInputData(1, selection)
        es.Update()

        ug = vedo.ugrid.UGrid(es.GetOutput())
        pr = vtk.vtkProperty()
        pr.DeepCopy(self.property)
        ug.SetProperty(pr)
        ug.property = pr

        ug.mapper.SetLookupTable(utils.ctf2lut(self))
        ug.pipeline = utils.OperationNode(
            "extract_cells_by_id",
            parents=[self],
            comment=f"#cells {self.dataset.GetNumberOfCells()}",
            c="#9e2a2b",
        )
        return ug

    def probe_points(self, pts):
        """
        Takes a `Volume` (or any other vtk data set)
        and probes its scalars at the specified points in space.

        Note that a mask is also output with valid/invalid points which can be accessed
        with `mesh.pointdata['vtkValidPointMask']`.

        Examples:
            - [probe_points.py](https://github.com/marcomusy/vedo/tree/master/examples/volumetric/probe_points.py)

                ![](https://vedo.embl.es/images/volumetric/probePoints.png)
        """
        if isinstance(pts, vedo.pointcloud.Points):
            pts = pts.vertices

        def _readpoints():
            output = src.GetPolyDataOutput()
            points = vtk.vtkPoints()
            for p in pts:
                x, y, z = p
                points.InsertNextPoint(x, y, z)
            output.SetPoints(points)

            cells = vtk.vtkCellArray()
            cells.InsertNextCell(len(pts))
            for i in range(len(pts)):
                cells.InsertCellPoint(i)
            output.SetVerts(cells)

        src = vtk.vtkProgrammableSource()
        src.SetExecuteMethod(_readpoints)
        src.Update()
        img = self.dataset
        probeFilter = vtk.vtkProbeFilter()
        probeFilter.SetSourceData(img)
        probeFilter.SetInputConnection(src.GetOutputPort())
        probeFilter.Update()
        poly = probeFilter.GetOutput()
        pm = vedo.mesh.Mesh(poly)
        pm.name = "ProbePoints"
        pm.pipeline = utils.OperationNode("probe_points", parents=[self])
        return pm


    def probe_line(self, p1, p2, res=100):
        """
        Takes a `Volume`  (or any other vtk data set)
        and probes its scalars along a line defined by 2 points `p1` and `p2`.

        Note that a mask is also output with valid/invalid points which can be accessed
        with `mesh.pointdata['vtkValidPointMask']`.

        Use `res` to set the nr of points along the line

        Examples:
            - [probe_line1.py](https://github.com/marcomusy/vedo/tree/master/examples/volumetric/probe_line1.py)
            - [probe_line2.py](https://github.com/marcomusy/vedo/tree/master/examples/volumetric/probe_line2.py)

                ![](https://vedo.embl.es/images/volumetric/probeLine2.png)
        """
        line = vtk.vtkLineSource()
        line.SetResolution(res)
        line.SetPoint1(p1)
        line.SetPoint2(p2)
        probeFilter = vtk.vtkProbeFilter()
        probeFilter.SetSourceData(self.dataset)
        probeFilter.SetInputConnection(line.GetOutputPort())
        probeFilter.Update()
        poly = probeFilter.GetOutput()
        lnn = vedo.mesh.Mesh(poly)
        lnn.name = "ProbeLine"
        lnn.pipeline = utils.OperationNode("probe_line", parents=[self])
        return lnn


    def probe_plane(self, origin=(0, 0, 0), normal=(1, 0, 0)):
        """
        Takes a `Volume` (or any other vtk data set)
        and probes its scalars on a plane defined by a point and a normal.

        Examples:
            - [slice_plane1.py](https://github.com/marcomusy/vedo/tree/master/examples/volumetric/slice_plane1.py)
            - [slice_plane2.py](https://github.com/marcomusy/vedo/tree/master/examples/volumetric/slice_plane2.py)

                ![](https://vedo.embl.es/images/volumetric/slicePlane2.png)
        """
        plane = vtk.vtkPlane()
        plane.SetOrigin(origin)
        plane.SetNormal(normal)
        planeCut = vtk.vtkCutter()
        planeCut.SetInputData(self.dataset)
        planeCut.SetCutFunction(plane)
        planeCut.Update()
        poly = planeCut.GetOutput()
        cutmesh = vedo.mesh.Mesh(poly)
        cutmesh.name = "ProbePlane"
        cutmesh.pipeline = utils.OperationNode("probe_plane", parents=[self])
        return cutmesh