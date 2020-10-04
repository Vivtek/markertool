import wx
import sys
from wxBufferedWindow import *
import Image

class ZoomingPILWindow(BufferedWindow):
     def __init__(self, *args, **kwargs):
         ## Any data the Draw() function needs must be initialized before
         ## calling BufferedWindow.__init__, as it will call the Draw
         ## function.
         if 'zoom' in kwargs:
            self.zoom = kwargs['zoom']
            del kwargs['zoom']
         else:
            self.zoom = 1
            
         if 'frame' in kwargs:
            self.frame = kwargs['frame']
            del kwargs['frame']
         else:
            self.frame = None

         if 'image' in kwargs:
            self.image = kwargs['image'].convert("RGB")
            self.native_size = self.image.size
            im = self.image.resize((self.native_size[0] * self.zoom, self.native_size[1] * self.zoom), Image.NEAREST)
            self.bitmap = wx.Bitmap.FromBuffer (im.size[0], im.size[1], im.tobytes())
            kwargs['size'] = im.size
            del kwargs['image']
         else:
            self.native_size = kwargs['size']
            self.image = Image.new("RBG", self.native_size, "white")
         
         BufferedWindow.__init__(self, *args, **kwargs)
         
     def SetImage(self, im):
         self.image = im.convert("RGB")
         self.native_size = im.size
         self.UpdateZoom()
         
     def SetZoom(self, zoom):
         self.zoom = zoom
         self.UpdateZoom()
         
     def ResizeDrawing(self, size):
         native_x = self.native_size[0]
         native_y = self.native_size[1]
         new_x = size[0]
         new_y = size[1]
         new_zoom = self.zoom

         if new_x > native_x * new_zoom and new_y > native_y * new_zoom:
            while (new_x >= native_x * (new_zoom + 1)) and (new_y >= native_y * (new_zoom + 1)):
               new_zoom += 1
         elif new_x < native_x * new_zoom and new_y < native_y * new_zoom:
            while new_zoom > 1 and (new_x <= native_x * (new_zoom - 1)) and (new_y <= native_y * (new_zoom - 1)):
               new_zoom -= 1
               
         if new_zoom != self.zoom:
            self.zoom = new_zoom
            if self.frame:
               self.frame.SetZoom(new_zoom)
            self.UpdateZoom()
         else:
            self.UpdateDrawing()
         
     def UpdateZoom(self):
         im = self.image.resize((self.native_size[0] * self.zoom, self.native_size[1] * self.zoom), Image.NEAREST)
         self.bitmap = wx.Bitmap.FromBuffer (im.size[0], im.size[1], im.tobytes())
         self.UpdateDrawing()
         
     def Draw(self, dc):
         dc.SetBackground( wx.Brush("White") )
         dc.Clear() # make sure you clear the bitmap!

         dc.DrawBitmap(self.bitmap, 0, 0)
         
         
class ZoomingPILFrame(wx.Frame):
    def __init__(self, *args, **kwargs):
    
        if 'parent' in kwargs:
           self.parent = kwargs['parent']
        else:
           self.parent = None

        if 'zoom' in kwargs:
           self.zoom = kwargs['zoom']
        else:
           self.zoom = 1
            
        if 'frame' in kwargs:
           self.frame = kwargs['frame']
        else:
           self.frame = None

        if 'image' in kwargs:
           self.image = kwargs['image'].convert("RGB")
           self.native_size = self.image.size
           im = self.image.resize((self.native_size[0] * self.zoom, self.native_size[1] * self.zoom), Image.NEAREST)
           self.bitmap = wx.Bitmap.FromBuffer (im.size[0], im.size[1], im.tobytes())
        else:
           self.native_size = kwargs['size'] # TODO : This is wrong.
           self.image = Image.new("RBG", self.native_size, "white")

        wx.Frame.__init__(self, self.parent,
                          size = (self.native_size[0]*self.zoom, self.native_size[1]*self.zoom),
                          title="Zoom x {}".format(self.zoom),
                          style=wx.DEFAULT_FRAME_STYLE)

        self.Window = ZoomingPILWindow(self, image = self.image, zoom = self.zoom, frame = self)
        self.Window.frame = self
        self.Show()
        
    def SetZoom(self, zoom):
        self.zoom = zoom
        self.SetTitle ("Zoom x {}".format(zoom))
        
    def SetImage(self, image):
        self.Window.SetImage (image)
        size  = self.GetSize()
        csize = self.GetClientSize()
        wdelta = size[0] - csize[0]
        hdelta = size[1] - csize[1]
        self.SetSize(image.size[0] * self.zoom + wdelta, image.size[1] * self.zoom + hdelta)

    def OnQuit(self,event):
        self.Close(True)


