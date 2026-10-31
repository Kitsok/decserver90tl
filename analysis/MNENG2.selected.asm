Selected code only. Addresses use inferred file bias 0x07805000.
68020 decoder mode does not establish the exact installed CPU.
These ranges do not establish the MOP transfer address.

File offset 0x200:
07805200  23cf07807254             move.l     a7, $7807254.l
07805206  4e7a8801                 movec      vbr, a0
0780520a  23c807807258             move.l     a0, $7807258.l
07805210  303c003f                 move.w     #$3f, d0
07805214  41f907805238             lea.l      $7805238.l, a0
0780521a  43f9078066d0             lea.l      $78066d0.l, a1
07805220  22d8                     move.l     (a0)+, (a1)+
07805222  51c8fffc                 dbra       d0, $7805220
07805226  303c00bf                 move.w     #$bf, d0
0780522a  72ff                     moveq      #$ff, d1
0780522c  22c1                     move.l     d1, (a1)+
0780522e  51c8fffc                 dbra       d0, $780522c
07805232  4ef90780535c             jmp        $780535c.l

File offset 0xa9a:
07805a9a  51f907807176             sf.b       $7807176.l
07805aa0  007c0700                 ori.w      #$700, sr
07805aa4  48f97fff078071e4         movem.l    d0-d7/a0-a6, $78071e4.l
07805aac  4bf907806e60             lea.l      $7806e60.l, a5
07805ab2  40c1                     move.w     sr, d1
07805ab4  261f                     move.l     (a7)+, d3
07805ab6  46fc2700                 move.w     #$2700, sr
07805aba  2b4f03c8                 move.l     a7, $3c8(a5)
07805abe  4fd5                     lea.l      (a5), a7
07805ac0  48e7f0e0                 movem.l    d0-d3/a0-a2, -(a7)
07805ac4  4eb9078065c6             jsr        $78065c6.l
07805aca  4cdf070f                 movem.l    (a7)+, d0-d3/a0-a2
07805ace  4e68                     move       usp, a0
07805ad0  2b4803cc                 move.l     a0, $3cc(a5)
07805ad4  4e7a0000                 movec      sfc, d0
07805ad8  1b4003d4                 move.b     d0, $3d4(a5)
07805adc  4e7a0001                 movec      dfc, d0
07805ae0  1b4003d5                 move.b     d0, $3d5(a5)
07805ae4  4e7a0801                 movec      vbr, d0
07805ae8  2b4003d0                 move.l     d0, $3d0(a5)
07805aec  422d0202                 clr.b      $202(a5)
07805af0  43faf746                 lea.l      $7805238(pc), a1
07805af4  4e7b9801                 movec      a1, vbr
07805af8  7800                     moveq      #$0, d4
07805afa  5983                     subq.l     #$4, d3
07805afc  41faf83a                 lea.l      $7805338(pc), a0
07805b00  9688                     sub.l      a0, d3
07805b02  0c430024                 cmpi.w     #$24, d3
07805b06  6620                     bne.b      $7805b28
07805b08  3b7cc3630314             move.w     #$c363, $314(a5)
07805b0e  3b4103ea                 move.w     d1, $3ea(a5)
07805b12  61000a30                 bsr.w      $7806544
07805b16  6100fb08                 bsr.w      $7805620
07805b1a  1b7c00000006             move.b     #$0, $6(a5)
07805b20  383c0200                 move.w     #$200, d4
07805b24  600000d4                 bra.w      $7805bfa
07805b28  0c6dc33b0314             cmpi.w     #$c33b, $314(a5)
07805b2e  6708                     beq.b      $7805b38
07805b30  0c6dc36d0314             cmpi.w     #$c36d, $314(a5)
07805b36  6630                     bne.b      $7805b68

File offset 0x2a02:
07807a02  4ef90780b650             jmp        $780b650.l

File offset 0x6650:
0780b650  41f9078051e6             lea.l      $78051e6.l, a0
0780b656  208f                     move.l     a7, (a0)
0780b658  4ff907bd5f50             lea.l      $7bd5f50.l, a7
0780b65e  4e7a8801                 movec      vbr, a0
0780b662  23c807bd3826             move.l     a0, $7bd3826.l
0780b668  203c000000ff             move.l     #$ff, d0
0780b66e  43f907807b3c             lea.l      $7807b3c.l, a1
0780b674  22d8                     move.l     (a0)+, (a1)+
0780b676  51c8fffc                 dbra       d0, $780b674
0780b67a  41f907807b3c             lea.l      $7807b3c.l, a0
0780b680  4e7b8801                 movec      a0, vbr
0780b684  46fc2600                 move.w     #$2600, sr
0780b688  4eb90780cf68             jsr        $780cf68.l
0780b68e  4eb90780cfb6             jsr        $780cfb6.l
0780b694  247907bd386c             movea.l    $7bd386c.l, a2
0780b69a  4eb907808dda             jsr        $7808dda.l
0780b6a0  42a7                     clr.l      -(a7)
0780b6a2  42a7                     clr.l      -(a7)
0780b6a4  487a002a                 pea.l      $780b6d0(pc)
0780b6a8  7200                     moveq      #$0, d1
0780b6aa  42a7                     clr.l      -(a7)
0780b6ac  243c00002400             move.l     #$2400, d2
0780b6b2  43f907bd5f50             lea.l      $7bd5f50.l, a1
0780b6b8  263c0000000a             move.l     #$a, d3
0780b6be  247c07807f3c             movea.l    #$7807f3c, a2
0780b6c4  4eb907808d3c             jsr        $7808d3c.l
0780b6ca  defc0010                 adda.w     #$10, a7
0780b6ce  6080                     bra.b      $780b650
0780b6d0  427907bd3824             clr.w      $7bd3824.l
0780b6d6  4eb90780d056             jsr        $780d056.l
0780b6dc  41f907805000             lea.l      $7805000.l, a0
0780b6e2  3228001e                 move.w     $1e(a0), d1
0780b6e6  760f                     moveq      #$f, d3
0780b6e8  0701                     btst.l     d3, d1
0780b6ea  6720                     beq.b      $780b70c
0780b6ec  48e75000                 movem.l    d1/d3, -(a7)
0780b6f0  4eb90780d8c0             jsr        $780d8c0.l
0780b6f6  2448                     movea.l    a0, a2
0780b6f8  2052                     movea.l    (a2), a0
0780b6fa  20280044                 move.l     $44(a0), d0
0780b6fe  6708                     beq.b      $780b708
