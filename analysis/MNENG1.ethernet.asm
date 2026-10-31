MNENG1: SHA-256 d4f5b755514cde7bb4840f27e35e3ea6a129bf1f8266f587aae3e708023e2226
Static disassembly, Capstone 68020 mode; not proof of exact CPU.
Register bit-operation suffixes/full-format EA text may be misleading.
Raw bytes are authoritative; see ethernet-controller.md for interpretation.

# LANCE initialize/start: linked 0x07835cf0, file 0x30cf0
07835cf0  207c00300000                 movea.l    #$300000, a0
07835cf6  317c00010002                 move.w     #$1, $2(a0)
07835cfc  203c07835880                 move.l     #$7835880, d0
07835d02  3080                         move.w     d0, (a0)
07835d04  4840                         swap       d0
07835d06  317c00020002                 move.w     #$2, $2(a0)
07835d0c  3080                         move.w     d0, (a0)
07835d0e  317c00030002                 move.w     #$3, $2(a0)
07835d14  30bc0006                     move.w     #$6, (a0)
07835d18  427907897ef8                 clr.w      $7897ef8.l
07835d1e  317c00000002                 move.w     #$0, $2(a0)
07835d24  30bc0001                     move.w     #$1, (a0)
07835d28  7001                         moveq      #$1, d0
07835d2a  7201                         moveq      #$1, d1
07835d2c  51c8fffe                     dbra       d0, $7835d2c
07835d30  3010                         move.w     (a0), d0
07835d32  08000008                     btst.b     #$8, d0
07835d36  660c                         bne.b      $7835d44
07835d38  5281                         addq.l     #$1, d1
07835d3a  2001                         move.l     d1, d0
07835d3c  23c107897edc                 move.l     d1, $7897edc.l
07835d42  60e8                         bra.b      $7835d2c
07835d44  30bc0100                     move.w     #$100, (a0)
07835d48  30bc0002                     move.w     #$2, (a0)
07835d4c  30bc0040                     move.w     #$40, (a0)
07835d50  4e75                         rts
