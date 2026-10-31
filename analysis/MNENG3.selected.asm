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
07807a02  4ef9078713f8             jmp        $78713f8.l

File offset 0x6c3f8:
078713f8  41f9078051e6             lea.l      $78051e6.l, a0
078713fe  208f                     move.l     a7, (a0)
07871400  4ff9079dbfc0             lea.l      $79dbfc0.l, a7
07871406  4e7a8801                 movec      vbr, a0
0787140a  303c00ff                 move.w     #$ff, d0
0787140e  43f90783b6ac             lea.l      $783b6ac.l, a1
07871414  22d8                     move.l     (a0)+, (a1)+
07871416  51c8fffc                 dbra       d0, $7871414
0787141a  41f90783b6ac             lea.l      $783b6ac.l, a0
07871420  4e7b8801                 movec      a0, vbr
07871424  46fc2600                 move.w     #$2600, sr
07871428  4eb9079404a8             jsr        $79404a8.l
0787142e  41f90798f9ac             lea.l      $798f9ac.l, a0
07871434  203c079dbfc0             move.l     #$79dbfc0, d0
0787143a  9088                     sub.l      a0, d0
0787143c  7203                     moveq      #$3, d1
0787143e  c280                     and.l      d0, d1
07871440  e488                     lsr.l      #$2, d0
07871442  6716                     beq.b      $787145a
07871444  5380                     subq.l     #$1, d0
07871446  4298                     clr.l      (a0)+
07871448  51c8fffc                 dbra       d0, $7871446
0787144c  4eb907941656             jsr        $7941656.l
07871452  048000010000             subi.l     #$10000, d0
07871458  64ec                     bcc.b      $7871446
0787145a  08810001                 bclr.b     #$1, d1
0787145e  6702                     beq.b      $7871462
07871460  4258                     clr.w      (a0)+
07871462  4a81                     tst.l      d1
07871464  6702                     beq.b      $7871468
07871466  4218                     clr.b      (a0)+
07871468  4eb9079404f6             jsr        $79404f6.l
0787146e  2479079ac138             movea.l    $79ac138.l, a2
07871474  4eb90787002c             jsr        $787002c.l
0787147a  42a7                     clr.l      -(a7)
0787147c  42a7                     clr.l      -(a7)
0787147e  487a002c                 pea.l      $78714ac(pc)
07871482  7200                     moveq      #$0, d1
07871484  42a7                     clr.l      -(a7)
07871486  243c00002400             move.l     #$2400, d2
0787148c  43f9079dbfc0             lea.l      $79dbfc0.l, a1
07871492  263c0000018b             move.l     #$18b, d3
07871498  247c0783baac             movea.l    #$783baac, a2
0787149e  4eb90786fefc             jsr        $786fefc.l
078714a4  defc0010                 adda.w     #$10, a7

File offset 0x13b4a8:
079404a8  45f9079404b4             lea.l      $79404b4.l, a2
079404ae  4ef90794458c             jmp        $794458c.l
079404b4  13c0078051e4             move.b     d0, $78051e4.l
079404ba  0079003700fffa18         ori.w      #$37, $fffa18.l
079404c2  0079000d00fffa10         ori.w      #$d, $fffa10.l
079404ca  4e7a8801                 movec      vbr, a0
079404ce  217c079455ec000c         move.l     #$79455ec, $c(a0)
079404d6  41f9fffff000             lea.l      $fffff000.l, a0
079404dc  43f9079448c4             lea.l      $79448c4.l, a1
079404e2  303c01fd                 move.w     #$1fd, d0
079404e6  0c4001ff                 cmpi.w     #$1ff, d0
079404ea  6302                     bls.b      $79404ee
079404ec  4afc                     illegal    #$4afc
079404ee  20d9                     move.l     (a1)+, (a0)+
079404f0  51c8fffc                 dbra       d0, $79404ee
079404f4  4e75                     rts        

File offset 0x13c656:
07941656  33fc005500fffa26         move.w     #$55, $fffa26.l
0794165e  33fc00aa00fffa26         move.w     #$aa, $fffa26.l
07941666  4e75                     rts        

File offset 0x2a68:
07807a68  103c00f7                 move.b     #$f7, d0
07807a6c  08390004079903ea         btst.b     #$4, $79903ea.l
07807a74  661a                     bne.b      $7807a90
07807a76  6100001a                 bsr.w      $7807a92
07807a7a  0c000001                 cmpi.b     #$1, d0
07807a7e  6710                     beq.b      $7807a90
07807a80  08f90004079903ea         bset.b     #$4, $79903ea.l
07807a88  6606                     bne.b      $7807a90
07807a8a  61ff00000e4a             bsr.l      $78088d6
