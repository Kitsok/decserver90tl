These are the only load images provided on the DNAS V3.3
CD. Apparently support for older hardware was dropped at
some earlier time.

The files here claim to support the following models.
Note that this has not been verified, except for the
DECserver 700-08, 700-16 and 900TM in the WWENG2.SYS
image. These model lists have been determined by ex-
amining the contents of the load image(s) and may not
be correct. Normally your DECserver will already be
configured to request the proper image.

mnboot.sys Boot EEPROM (NOT operating firmware):
  DECserver 90M+

mneng4.sys:
  DECserver 90TL
  DECserver 90M/90M+
  DECserver ConX4 and ConX4P

wweng2.sys:
  DECserver 700-08, tested working no flash card slot (needs at least 4MB of RAM)
  DECserver 700-16, tested working including updating flash card (needs at least 4MB of RAM)
  DECserver 700-32
  DECserver 900GM 
  DECserver 900TM, tested working including updating flash card
  DECserver 900MC 
  DECserver 900GM/900GMx
  Cabletron 316   
  Cabletron 708
  Cabletron 716   
  Cabletron 732   
