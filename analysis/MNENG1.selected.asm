Selected code only. Addresses use inferred file bias 0x07805000.
68020 decoder mode does not establish the exact installed CPU.
These ranges do not establish the MOP transfer address.

File offset 0x200:
07805200  23cf078071f8             move.l     a7, $78071f8.l
07805206  4e7a8801                 movec      vbr, a0
0780520a  23c8078071fc             move.l     a0, $78071fc.l
07805210  303c003f                 move.w     #$3f, d0
07805214  41f907805238             lea.l      $7805238.l, a0
0780521a  43f907806674             lea.l      $7806674.l, a1
07805220  22d8                     move.l     (a0)+, (a1)+
07805222  51c8fffc                 dbra       d0, $7805220
07805226  303c00bf                 move.w     #$bf, d0
0780522a  72ff                     moveq      #$ff, d1
0780522c  22c1                     move.l     d1, (a1)+
0780522e  51c8fffc                 dbra       d0, $780522c
07805232  4ef90780535c             jmp        $780535c.l

File offset 0xa9a:
07805a9a  51f90780711a             sf.b       $780711a.l
07805aa0  007c0700                 ori.w      #$700, sr
07805aa4  48f97fff07807188         movem.l    d0-d7/a0-a6, $7807188.l
07805aac  4bf907806e04             lea.l      $7806e04.l, a5
07805ab2  40c1                     move.w     sr, d1
07805ab4  261f                     move.l     (a7)+, d3
07805ab6  46fc2700                 move.w     #$2700, sr
07805aba  2b4f03c8                 move.l     a7, $3c8(a5)
07805abe  4fd5                     lea.l      (a5), a7
07805ac0  48e7f0e0                 movem.l    d0-d3/a0-a2, -(a7)
07805ac4  4eb90780655c             jsr        $780655c.l
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
07805b12  610009b4                 bsr.w      $78064c8
07805b16  6100fb08                 bsr.w      $7805620
07805b1a  1b7c00000006             move.b     #$0, $6(a5)
07805b20  383c0200                 move.w     #$200, d4
07805b24  600000d4                 bra.w      $7805bfa
07805b28  0c6dc33b0314             cmpi.w     #$c33b, $314(a5)
07805b2e  6708                     beq.b      $7805b38
07805b30  0c6dc36d0314             cmpi.w     #$c36d, $314(a5)
07805b36  6630                     bne.b      $7805b68

File offset 0x2a00:
07807a00  4ef907832b94             jmp        $7832b94.l

File offset 0x2db94:
07832b94  41f9078051e6             lea.l      $78051e6.l, a0
07832b9a  208f                     move.l     a7, (a0)
07832b9c  4ff9078c7290             lea.l      $78c7290.l, a7
07832ba2  4e7a8801                 movec      vbr, a0
07832ba6  303c00ff                 move.w     #$ff, d0
07832baa  43f90782ad58             lea.l      $782ad58.l, a1
07832bb0  22d8                     move.l     (a0)+, (a1)+
07832bb2  51c8fffc                 dbra       d0, $7832bb0
07832bb6  41f90782ad58             lea.l      $782ad58.l, a0
07832bbc  4e7b8801                 movec      a0, vbr
07832bc0  46fc2600                 move.w     #$2600, sr
07832bc4  4eb90788cd08             jsr        $788cd08.l
07832bca  41f907895d98             lea.l      $7895d98.l, a0
07832bd0  203c078c7290             move.l     #$78c7290, d0
07832bd6  9088                     sub.l      a0, d0
07832bd8  7203                     moveq      #$3, d1
07832bda  c280                     and.l      d0, d1
07832bdc  e488                     lsr.l      #$2, d0
07832bde  6716                     beq.b      $7832bf6
07832be0  5380                     subq.l     #$1, d0
07832be2  4298                     clr.l      (a0)+
07832be4  51c8fffc                 dbra       d0, $7832be2
07832be8  4eb90788d5d8             jsr        $788d5d8.l
07832bee  048000010000             subi.l     #$10000, d0
07832bf4  64ec                     bcc.b      $7832be2
07832bf6  08810001                 bclr.b     #$1, d1
07832bfa  6702                     beq.b      $7832bfe
07832bfc  4258                     clr.w      (a0)+
07832bfe  4a81                     tst.l      d1
07832c00  6702                     beq.b      $7832c04
07832c02  4218                     clr.b      (a0)+
07832c04  4eb90788cd56             jsr        $788cd56.l
07832c0a  2479078a06d4             movea.l    $78a06d4.l, a2
07832c10  4eb9078927e4             jsr        $78927e4.l
07832c16  42a7                     clr.l      -(a7)
07832c18  42a7                     clr.l      -(a7)
07832c1a  487a002c                 pea.l      $7832c48(pc)
07832c1e  7200                     moveq      #$0, d1
07832c20  42a7                     clr.l      -(a7)
07832c22  243c00001800             move.l     #$1800, d2
07832c28  43f9078c7290             lea.l      $78c7290.l, a1
07832c2e  263c00000088             move.l     #$88, d3
07832c34  247c0782b158             movea.l    #$782b158, a2
07832c3a  4eb907893b0a             jsr        $7893b0a.l
07832c40  defc0010                 adda.w     #$10, a7
