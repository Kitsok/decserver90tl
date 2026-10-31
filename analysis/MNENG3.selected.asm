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

File offset 0x13b9e2:
079409e2  40c1                     move.w     sr, d1
079409e4  46fc2600                 move.w     #$2600, sr
079409e8  43f900200000             lea.l      $200000.l, a1
079409ee  7005                     moveq      #$5, d0
079409f0  14d1                     move.b     (a1), (a2)+
079409f2  5289                     addq.l     #$1, a1
079409f4  51c8fffa                 dbra       d0, $79409f0
079409f8  46c1                     move.w     d1, sr
079409fa  4e75                     rts

File offset 0x13ce50:
07941e50  41f907941e04             lea.l      $7941e04.l, a0
07941e56  4280                     clr.l      d0
07941e58  e58b                     lsl.l      #$2, d3
07941e5a  30303000                 move.w     (a0, d3.w), d0
07941e5e  068000fffa00             addi.l     #$fffa00, d0
07941e64  2240                     movea.l    d0, a1
07941e66  5483                     addq.l     #$2, d3
07941e68  4280                     clr.l      d0
07941e6a  30303000                 move.w     (a0, d3.w), d0
07941e6e  0191                     bclr.b     d0, (a1)
07941e70  4e75                     rts
07941e72  41f907941e04             lea.l      $7941e04.l, a0
07941e78  4280                     clr.l      d0
07941e7a  e58b                     lsl.l      #$2, d3
07941e7c  30303000                 move.w     (a0, d3.w), d0
07941e80  068000fffa00             addi.l     #$fffa00, d0
07941e86  2240                     movea.l    d0, a1
07941e88  5483                     addq.l     #$2, d3
07941e8a  4280                     clr.l      d0
07941e8c  30303000                 move.w     (a0, d3.w), d0
07941e90  01d1                     bset.b     d0, (a1)
07941e92  4e75                     rts

File offset 0x13d318:
07942318  2491                     move.l     (a1), (a2)
0794231a  256900040004             move.l     $4(a1), $4(a2)
07942320  35690012289e             move.w     $12(a1), $289e(a2)
07942326  48e70060                 movem.l    a1-a2, -(a7)
0794232a  22690008                 movea.l    $8(a1), a1
0794232e  45ea0008                 lea.l      $8(a2), a2
07942332  6100feee                 bsr.w      $7942222
07942336  4cdf0600                 movem.l    (a7)+, a1-a2
0794233a  48e70060                 movem.l    a1-a2, -(a7)
0794233e  2269000c                 movea.l    $c(a1), a1
07942342  45ea1450                 lea.l      $1450(a2), a2
07942346  6100feda                 bsr.w      $7942222
0794234a  4cdf0600                 movem.l    (a7)+, a1-a2
0794234e  422a2898                 clr.b      $2898(a2)
07942352  422a2899                 clr.b      $2899(a2)
07942356  422a289a                 clr.b      $289a(a2)
0794235a  422a289b                 clr.b      $289b(a2)
0794235e  422a289c                 clr.b      $289c(a2)
07942362  4e75                     rts

File offset 0x13d560:
07942560  2f0d                     move.l     a5, -(a7)
07942562  42b9079ac750             clr.l      $79ac750.l
07942568  4bf90794253c             lea.l      $794253c.l, a5
0794256e  201d                     move.l     (a5)+, d0
07942570  23c0079ac74c             move.l     d0, $79ac74c.l
07942576  670c                     beq.b      $7942584
07942578  2440                     movea.l    d0, a2
0794257a  225d                     movea.l    (a5)+, a1
0794257c  6100fd9a                 bsr.w      $7942318
07942580  201d                     move.l     (a5)+, d0
07942582  66f4                     bne.b      $7942578
07942584  2a5f                     movea.l    (a7)+, a5
07942586  4e75                     rts
07942588  2f0d                     move.l     a5, -(a7)

File offset 0x13d5aa:
079425aa  2f0d                     move.l     a5, -(a7)
079425ac  2a52                     movea.l    (a2), a5
079425ae  1b7c00900004             move.b     #$90, $4(a5)
079425b4  4a97                     tst.l      (a7)
079425b6  4a97                     tst.l      (a7)
079425b8  1b7c00900014             move.b     #$90, $14(a5)
079425be  4a97                     tst.l      (a7)
079425c0  4a97                     tst.l      (a7)
079425c2  157c0080289c             move.b     #$80, $289c(a2)
079425c8  1b6a289c001a             move.b     $289c(a2), $1a(a5)
079425ce  157c00e02898             move.b     #$e0, $2898(a2)
079425d4  1b6a28980008             move.b     $2898(a2), $8(a5)
079425da  157c00002899             move.b     #$0, $2899(a2)
079425e0  1b6a2899000a             move.b     $2899(a2), $a(a5)
079425e6  4a2d0008                 tst.b      $8(a5)

File offset 0x13f58c:
0794458c  303c0044                 move.w     #$44, d0
07944590  41fb0170fff27d5a         lea.l      $fff27d5a(a16, invalid.w), a0
07944598  3218                     move.w     (a0)+, d1
0794459a  3258                     movea.w    (a0)+, a1
0794459c  3281                     move.w     d1, (a1)
0794459e  51c8fff8                 dbra       d0, $7944598
079445a2  08380006fc15             btst.b     #$6, $fc15.w
079445a8  6638                     bne.b      $79445e2
079445aa  08380004fa07             btst.b     #$4, $fa07.w
079445b0  6730                     beq.b      $79445e2
079445b2  223c012357bd             move.l     #$12357bd, d1
079445b8  41f9fffff000             lea.l      $fffff000.l, a0
079445be  303c01ff                 move.w     #$1ff, d0
079445c2  b290                     cmp.l      (a0), d1
079445c4  661c                     bne.b      $79445e2
079445c6  4698                     not.l      (a0)+
079445c8  e399                     rol.l      #$1, d1
079445ca  51c8fff6                 dbra       d0, $79445c2
079445ce  31fc008cfa20             move.w     #$8c, $fa20.w
079445d4  31fc0055fa26             move.w     #$55, $fa26.w
079445da  31fc00aafa26             move.w     #$aa, $fa26.w
079445e0  60fe                     bra.b      $79445e0
079445e2  31fc00ecfa20             move.w     #$ec, $fa20.w
079445e8  31fc0055fa26             move.w     #$55, $fa26.w
079445ee  31fc00aafa26             move.w     #$aa, $fa26.w
079445f4  6002                     bra.b      $79445f8
079445f6  4e71                     nop
079445f8  00780c00fe18             ori.w      #$c00, $fe18.w
079445fe  3238fe18                 move.w     $fe18.w, d1
07944602  02410c00                 andi.w     #$c00, d1
07944606  66f6                     bne.b      $79445fe
07944608  7402                     moveq      #$2, d2
0794460a  4a78ffd2                 tst.w      $ffd2.w
0794460e  6b24                     bmi.b      $7944634
07944610  704f                     moveq      #$4f, d0
07944612  4e71                     nop
07944614  51c8fffc                 dbra       d0, $7944612
07944618  00780c00fe18             ori.w      #$c00, $fe18.w
0794461e  3238fe18                 move.w     $fe18.w, d1
07944622  02410c00                 andi.w     #$c00, d1
07944626  66f6                     bne.b      $794461e
07944628  4a78ffd2                 tst.w      $ffd2.w
0794462c  5bcaffe2                 dbmi       d2, $7944610
07944630  6b26                     bmi.b      $7944658
07944632  6040                     bra.b      $7944674
07944634  704f                     moveq      #$4f, d0
07944636  4e71                     nop
07944638  51c8fffc                 dbra       d0, $7944636
0794463c  00780c00fe18             ori.w      #$c00, $fe18.w
07944642  3238fe18                 move.w     $fe18.w, d1
07944646  02410c00                 andi.w     #$c00, d1
0794464a  66f6                     bne.b      $7944642
0794464c  4a78ffd2                 tst.w      $ffd2.w
07944650  5acaffe2                 dbpl       d2, $7944634
07944654  6a02                     bpl.b      $7944658
07944656  6038                     bra.b      $7944690
07944658  31fc0037fc16             move.w     #$37, $fc16.w
0794465e  31fc0000fc14             move.w     #$0, $fc14.w
07944664  31fc0008fc14             move.w     #$8, $fc14.w
0794466a  31fc00c8fa1e             move.w     #$c8, $fa1e.w
07944670  7002                     moveq      #$2, d0
07944672  4ed2                     jmp        (a2)
07944674  31fc003ffc16             move.w     #$3f, $fc16.w
0794467a  31fc0000fc14             move.w     #$0, $fc14.w
07944680  31fc0008fc14             move.w     #$8, $fc14.w
07944686  31fc00c8fa1e             move.w     #$c8, $fa1e.w
0794468c  7003                     moveq      #$3, d0
0794468e  4ed2                     jmp        (a2)
07944690  4280                     clr.l      d0
07944692  42390040003a             clr.b      $40003a.l
07944698  12390040003a             move.b     $40003a.l, d1
0794469e  08010004                 btst.b     #$4, d1

File offset 0x13f690:
07944690  4280                     clr.l      d0
07944692  42390040003a             clr.b      $40003a.l
07944698  12390040003a             move.b     $40003a.l, d1
0794469e  08010004                 btst.b     #$4, d1
079446a2  6704                     beq.b      $79446a8
079446a4  08c00000                 bset.b     #$0, d0
079446a8  08010006                 btst.b     #$6, d1
079446ac  6704                     beq.b      $79446b2
079446ae  08c00001                 bset.b     #$1, d0
079446b2  5880                     addq.l     #$4, d0
079446b4  31fc003cfc16             move.w     #$3c, $fc16.w
079446ba  31fc0000fc14             move.w     #$0, $fc14.w
079446c0  31fc0008fc14             move.w     #$8, $fc14.w
079446c6  31fc00c8fa1e             move.w     #$c8, $fa1e.w
079446cc  31fc4007fa64             move.w     #$4007, $fa64.w
079446d2  33fc005c00440000         move.w     #$5c, $440000.l
079446da  31fc6007fa50             move.w     #$6007, $fa50.w
079446e0  31fc7870fa52             move.w     #$7870, $fa52.w
079446e6  31fc7007fa54             move.w     #$7007, $fa54.w
079446ec  31fc7870fa56             move.w     #$7870, $fa56.w
079446f2  4ed2                     jmp        (a2)

File offset 0x13f6f4:
079446f4  33fc000000fffa22         move.w     #$0, $fffa22.l
079446fc  33fc000000fffa24         move.w     #$0, $fffa24.l
07944704  0279cfff00fffe1c         andi.w     #$cfff, $fffe1c.l
0794470c  4a3900200000             tst.b      $200000.l
07944712  4e7a9801                 movec      vbr, a1
07944716  237cfffff1840078         move.l     #$fffff184, $78(a1)
0794471e  4e75                     rts

File offset 0x13fa48:
07944a48  4a3900200000             tst.b      $200000.l
07944a4e  5238fd4c                 addq.b     #$1, $fd4c.w
07944a52  5338f0cf                 subq.b     #$1, $f0cf.w
07944a56  679e                     beq.b      $79449f6
07944a58  4a8f                     tst.l      a7
07944a5a  6d0e                     blt.b      $7944a6a
07944a5c  3f04                     move.w     d4, -(a7)
07944a5e  3838fe20                 move.w     $fe20.w, d4
07944a62  c878f02e                 and.w      $f02e.w, d4
07944a66  6604                     bne.b      $7944a6c
07944a68  381f                     move.w     (a7)+, d4
07944a6a  4e73                     rte
07944a6c  4a04                     tst.b      d4
07944a6e  660000a2                 bne.w      $7944b12
07944a72  4a44                     tst.w      d4
07944a74  67f2                     beq.b      $7944a68
07944a76  08f80001f0ce             bset.b     #$1, $f0ce.w
07944a7c  66ea                     bne.b      $7944a68
07944a7e  60000196                 bra.w      $7944c16
07944a82  5538f0ce                 subq.b     #$2, $f0ce.w
07944a86  60e0                     bra.b      $7944a68

File offset 0x13fb12:
07944b12  48f88f2ffd00             movem.l    d0-d3/d5/a0-a3/a7, $fd00.w
07944b18  3e7cf0c4                 movea.w    #$f0c4, a7
07944b1c  50f8fd4c                 st.b       $fd4c.w
07944b20  46fc2500                 move.w     #$2500, sr
07944b24  47f8f030                 lea.l      $f030.w, a3
07944b28  43f900400000             lea.l      $400000.l, a1
07944b2e  343c00f0                 move.w     #$f0, d2
07944b32  7a07                     moveq      #$7, d5
07944b34  4604                     not.b      d4
07944b36  11c4fe21                 move.b     d4, $fe21.w
07944b3a  4604                     not.b      d4
07944b3c  e30c                     lsl.b      #$1, d4
07944b3e  53cdfffc                 dbls       d5, $7944b3c
07944b42  6434                     bcc.b      $7944b78
07944b44  3005                     move.w     d5, d0
07944b46  d040                     add.w      d0, d0
07944b48  41f10602                 lea.l      $2(a1, d0.w), a0
07944b4c  1610                     move.b     (a0), d3
07944b4e  08030000                 btst.b     #$0, d3
07944b52  6720                     beq.b      $7944b74
07944b54  72ff                     moveq      #$ff, d1
07944b56  244b                     movea.l    a3, a2
07944b58  588b                     addq.l     #$4, a3
07944b5a  3003                     move.w     d3, d0
07944b5c  c042                     and.w      d2, d0
07944b5e  6634                     bne.b      $7944b94
07944b60  10280004                 move.b     $4(a0), d0
07944b64  1610                     move.b     (a0), d3
07944b66  5241                     addq.w     #$1, d1
07944b68  36c0                     move.w     d0, (a3)+
07944b6a  08030000                 btst.b     #$0, d3
07944b6e  66ea                     bne.b      $7944b5a
07944b70  34c1                     move.w     d1, (a2)+
07944b72  34c5                     move.w     d5, (a2)+
07944b74  51cdffc6                 dbra       d5, $7944b3c

File offset 0x13fc16:
07944c16  48f81f22fd28             movem.l    d1/d5/a0-a4, $fd28.w
07944c1c  7a03                     moveq      #$3, d5
07944c1e  4644                     not.w      d4
07944c20  31c4fe20                 move.w     d4, $fe20.w
07944c24  4644                     not.w      d4
07944c26  e94c                     lsl.w      #$4, d4
07944c28  e34c                     lsl.w      #$1, d4
07944c2a  53cdfffc                 dbls       d5, $7944c28
07944c2e  6420                     bcc.b      $7944c50
07944c30  46fc2500                 move.w     #$2500, sr
07944c34  46fc2600                 move.w     #$2600, sr
07944c38  267057a0f000             movea.l    $f000(d5.w * 8), a3
07944c3e  286bffec                 movea.l    -$14(a3), a4
07944c42  122b2885                 move.b     $2885(a3), d1
07944c46  c22c000a                 and.b      $a(a4), d1
07944c4a  6618                     bne.b      $7944c64
07944c4c  51cdffda                 dbra       d5, $7944c28
07944c50  4cf81f22fd28             movem.l    $fd28.w, d1/d5/a0-a4
07944c56  6000fe2a                 bra.w      $7944a82
07944c5a  46fc2500                 move.w     #$2500, sr
07944c5e  46fc2600                 move.w     #$2600, sr
07944c62  60de                     bra.b      $7944c42
07944c64  08010000                 btst.b     #$0, d1
07944c68  670a                     beq.b      $7944c74
07944c6a  45eb1120                 lea.l      $1120(a3), a2
07944c6e  43ec0006                 lea.l      $6(a4), a1
07944c72  600e                     bra.b      $7944c82
07944c74  08010004                 btst.b     #$4, d1
07944c78  6732                     beq.b      $7944cac
07944c7a  45eb2568                 lea.l      $2568(a3), a2
07944c7e  43ec0016                 lea.l      $16(a4), a1
07944c82  222affe8                 move.l     -$18(a2), d1
07944c86  6a18                     bpl.b      $7944ca0
07944c88  2052                     movea.l    (a2), a0
07944c8a  1298                     move.b     (a0)+, (a1)
07944c8c  2488                     move.l     a0, (a2)
07944c8e  536a000a                 subq.w     #$1, $a(a2)
07944c92  66ae                     bne.b      $7944c42
07944c94  45eaeed4                 lea.l      -$112c(a2), a2
07944c98  4eb9079440e2             jsr        $79440e2.l
07944c9e  60ba                     bra.b      $7944c5a
07944ca0  5989                     subq.l     #$4, a1
07944ca2  45eaeed4                 lea.l      -$112c(a2), a2
07944ca6  2041                     movea.l    d1, a0
07944ca8  4e90                     jsr        (a0)

File offset 0x140300:
07945300  48e76060                 movem.l    d1-d2/a1-a2, -(a7)
07945304  45f8f0c4                 lea.l      $f0c4.w, a2
07945308  43f90040001a             lea.l      $40001a.l, a1
0794530e  7420                     moveq      #$20, d2
07945310  7203                     moveq      #$3, d1
07945312  1611                     move.b     (a1), d3
07945314  871a                     or.b       d3, (a2)+
07945316  c71a                     and.b      d3, (a2)+
07945318  d2c2                     adda.w     d2, a1
0794531a  51c9fff6                 dbra       d1, $7945312
0794531e  4cdf0606                 movem.l    (a7)+, d1-d2/a1-a2
07945322  261f                     move.l     (a7)+, d3
07945324  4e75                     rts

File offset 0x1421a8:
079471a8  6b9e                     bmi.b      $7947148
079471aa  2a3c079b6b98             move.l     #$79b6b98, d5
079471b0  2c3c079b6b90             move.l     #$79b6b90, d6
079471b6  2e3c079b6b9a             move.l     #$79b6b9a, d7
079471bc  70ff                     moveq      #$ff, d0
079471be  3f400020                 move.w     d0, $20(a7)
079471c2  3f400022                 move.w     d0, $22(a7)
079471c6  0079000100440000         ori.w      #$1, $440000.l
079471ce  263c00003039             move.l     #$3039, d3
079471d4  4eb907941a78             jsr        $7941a78.l
079471da  33fc909000600000         move.w     #$9090, $600000.l
079471e2  3f79006000000022         move.w     $600000.l, $22(a7)
079471ea  3f79006000020020         move.w     $600002.l, $20(a7)
079471f2  0c2f00890022             cmpi.b     #$89, $22(a7)
079471f8  6708                     beq.b      $7947202
079471fa  102f0022                 move.b     $22(a7), d0
079471fe  5300                     subq.b     #$1, d0
07947200  662c                     bne.b      $794722e
07947202  33fcffff00600000         move.w     #$ffff, $600000.l
0794720a  33fcffff00600000         move.w     #$ffff, $600000.l
07947212  4294                     clr.l      (a4)
07947214  2046                     movea.l    d6, a0
07947216  4290                     clr.l      (a0)
07947218  2045                     movea.l    d5, a0
0794721a  10bc0001                 move.b     #$1, (a0)
0794721e  2047                     movea.l    d7, a0
07947220  30bc0001                 move.w     #$1, (a0)
07947224  4253                     clr.w      (a3)
07947226  2044                     movea.l    d4, a0
07947228  30bc00a2                 move.w     #$a2, (a0)
0794722c  606c                     bra.b      $794729a
0794722e  33fcf0f000600000         move.w     #$f0f0, $600000.l
07947236  7624                     moveq      #$24, d3
07947238  4eb907941a78             jsr        $7941a78.l
0794723e  33fcaaaa00600aaa         move.w     #$aaaa, $600aaa.l
07947246  33fc555500600554         move.w     #$5555, $600554.l
0794724e  33fc909000600aaa         move.w     #$9090, $600aaa.l
07947256  3f79                     move.w     $aaaaaaaa.l, -$5556(a7)
