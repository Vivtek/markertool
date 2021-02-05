#---------------------------------------------------------------------------
# Taken from https://wiki.wxpython.org/DoubleBufferedDrawing
# Updated to work with Phoenix
#---------------------------------------------------------------------------

import wx
import sys
from PIL import Image

from wxBufferedWindow import *
class BufferedBitmapWindow(BufferedWindow):
     def __init__(self, *args, **kwargs):
         ## Any data the Draw() function needs must be initialized before
         ## calling BufferedWindow.__init__, as it will call the Draw
         ## function.
         self.bitmap = wx.Bitmap(kwargs['size'])
         BufferedWindow.__init__(self, *args, **kwargs)
         
     def SetBitmap(self, bitmap):
         self.bitmap = bitmap
         self.UpdateDrawing()
 
     def Draw(self, dc):
         dc.SetBackground( wx.Brush("White") )
         dc.Clear() # make sure you clear the bitmap!

         dc.DrawBitmap(self.bitmap, 0, 0)
         
