MNENG3: SHA-256 a3764087d79df64eb7124056824652cf23b558fcae2029f887e4a37a3db49ad3
Static disassembly, Capstone 68020 mode; not proof of exact CPU.
Register bit-operation suffixes/full-format EA text may be misleading.
Raw bytes are authoritative; see ethernet-controller.md for interpretation.

# Operating software initializes network interface: linked 0x078740fa, file 0x6f0fa
078740fa  48e7f0c0                     movem.l    d0-d3/a0-a1, -(a7)
078740fe  6106                         bsr.b      $7874106
07874100  4cdf030f                     movem.l    (a7)+, d0-d3/a0-a1
07874104  4e75                         rts
07874106  4280                         clr.l      d0
07874108  083900000798fa29             btst.b     #$0, $798fa29.l
07874110  6602                         bne.b      $7874114
07874112  7001                         moveq      #$1, d0
07874114  2f0d                         move.l     a5, -(a7)
07874116  2f00                         move.l     d0, -(a7)
07874118  2f3c0798f9b0                 move.l     #$798f9b0, -(a7)
0787411e  48780002                     pea.l      $2.w
07874122  2a4f                         movea.l    a7, a5
07874124  4eb907874138                 jsr        $7874138.l
0787412a  defc000c                     adda.w     #$c, a7
0787412e  2a5f                         movea.l    (a7)+, a5
07874130  4eb9078744ea                 jsr        $78744ea.l
07874136  4e75                         rts

# Stop controller, prepare station address and RX ring: linked 0x07874144, file 0x6f144
07874144  52b90799eb7e                 addq.l     #$1, $799eb7e.l
0787414a  6406                         bcc.b      $7874152
0787414c  52b90799eb76                 addq.l     #$1, $799eb76.l
07874152  207c00300000                 movea.l    #$300000, a0
07874158  317c00000002                 move.w     #$0, $2(a0)
0787415e  30bc0004                     move.w     #$4, (a0)
07874162  226d0004                     movea.l    $4(a5), a1
07874166  23d10799ea44                 move.l     (a1), $799ea44.l
0787416c  33e900040799ea48             move.w     $4(a1), $799ea48.l
07874174  203c0799ea4a                 move.l     #$799ea4a, d0
0787417a  4840                         swap       d0
0787417c  024000ff                     andi.w     #$ff, d0
07874180  00408100                     ori.w      #$8100, d0
07874184  23c00799ea4a                 move.l     d0, $799ea4a.l
0787418a  42390799ea43                 clr.b      $799ea43.l
07874190  13fc00010799ea43             move.b     #$1, $799ea43.l
07874198  247c07873e06                 movea.l    #$7873e06, a2
0787419e  7002                         moveq      #$2, d0
078741a0  15590001                     move.b     (a1)+, $1(a2)
078741a4  1499                         move.b     (a1)+, (a2)
078741a6  548a                         addq.l     #$2, a2
078741a8  51c8fff6                     dbra       d0, $78741a0
078741ac  4a390799ea43                 tst.b      $799ea43.l
078741b2  6606                         bne.b      $78741ba
078741b4  4a2d000b                     tst.b      $b(a5)
078741b8  6708                         beq.b      $78741c2
078741ba  08f900020799ea42             bset.b     #$2, $799ea42.l
078741c2  203c0799ec08                 move.l     #$799ec08, d0
078741c8  020000f8                     andi.b     #$f8, d0
078741cc  2240                         movea.l    d0, a1
078741ce  45f90799ea14                 lea.l      $799ea14.l, a2
078741d4  24c0                         move.l     d0, (a2)+
078741d6  24c0                         move.l     d0, (a2)+
078741d8  24c0                         move.l     d0, (a2)+
078741da  267c07873e14                 movea.l    #$7873e14, a3
078741e0  2200                         move.l     d0, d1
078741e2  028100ffffff                 andi.l     #$ffffff, d1
078741e8  4841                         swap       d1
078741ea  0041a000                     ori.w      #$a000, d1
078741ee  2681                         move.l     d1, (a3)
078741f0  0680000000f8                 addi.l     #$f8, d0
078741f6  24c0                         move.l     d0, (a2)+
078741f8  068000000008                 addi.l     #$8, d0
078741fe  24c0                         move.l     d0, (a2)+
07874200  24c0                         move.l     d0, (a2)+
07874202  24c0                         move.l     d0, (a2)+

# TX ring and ring clearing: linked 0x07874204, file 0x6f204
07874204  267c07873e18                 movea.l    #$7873e18, a3
0787420a  2200                         move.l     d0, d1
0787420c  028100ffffff                 andi.l     #$ffffff, d1
07874212  4841                         swap       d1
07874214  00416000                     ori.w      #$6000, d1
07874218  2681                         move.l     d1, (a3)
0787421a  068000000038                 addi.l     #$38, d0
07874220  24c0                         move.l     d0, (a2)+
07874222  703f                         moveq      #$3f, d0
07874224  22790799ea14                 movea.l    $799ea14.l, a1
0787422a  4299                         clr.l      (a1)+
0787422c  51c8fffc                     dbra       d0, $787422a
07874230  303c007f                     move.w     #$7f, d0
07874234  22790799ea14                 movea.l    $799ea14.l, a1
0787423a  6008                         bra.b      $7874244
0787423c  700f                         moveq      #$f, d0
0787423e  4299                         clr.l      (a1)+
07874240  51c8fffc                     dbra       d0, $787423e

# Initial receive buffer population: linked 0x07874352, file 0x6f352
07874352  700f                         moveq      #$f, d0
07874354  41f9079cabc0                 lea.l      $79cabc0.l, a0
0787435a  41e80012                     lea.l      $12(a0), a0
0787435e  2f0d                         move.l     a5, -(a7)
07874360  2f08                         move.l     a0, -(a7)
07874362  48780001                     pea.l      $1.w
07874366  2a4f                         movea.l    a7, a5
07874368  4eb907874586                 jsr        $7874586.l
0787436e  defc0008                     adda.w     #$8, a7
07874372  2a5f                         movea.l    (a7)+, a5
07874374  d0fc0600                     adda.w     #$600, a0
07874378  51c8ffe4                     dbra       d0, $787435e
0787437c  4e75                         rts

# Stop controller: linked 0x078744c8, file 0x6f4c8
078744c8  207c00300000                 movea.l    #$300000, a0
078744ce  317c00000002                 move.w     #$0, $2(a0)
078744d4  4280                         clr.l      d0
078744d6  3010                         move.w     (a0), d0
078744d8  30bc0004                     move.w     #$4, (a0)
078744dc  08000002                     btst.b     #$2, d0
078744e0  6606                         bne.b      $78744e8
078744e2  33c00799ea34                 move.w     d0, $799ea34.l
078744e8  4e75                         rts

# LANCE initialize/start: linked 0x078744f6, file 0x6f4f6
078744f6  207c00300000                 movea.l    #$300000, a0
078744fc  317c00010002                 move.w     #$1, $2(a0)
07874502  203c07873e04                 move.l     #$7873e04, d0
07874508  3080                         move.w     d0, (a0)
0787450a  4840                         swap       d0
0787450c  317c00020002                 move.w     #$2, $2(a0)
07874512  3080                         move.w     d0, (a0)
07874514  317c00030002                 move.w     #$3, $2(a0)
0787451a  30bc0006                     move.w     #$6, (a0)
0787451e  317c00000002                 move.w     #$0, $2(a0)
07874524  30bc0041                     move.w     #$41, (a0)
07874528  7064                         moveq      #$64, d0
0787452a  51c8fffe                     dbra       d0, $787452a
0787452e  3010                         move.w     (a0), d0
07874530  08000008                     btst.b     #$8, d0
07874534  6628                         bne.b      $787455e
07874536  23fc0787453607805028         move.l     #$7874536, $7805028.l
07874540  40f907805030                 move.w     sr, $7805030.l
07874546  33fc021207805036             move.w     #$212, $7805036.l
0787454e  23fc0000000007805032         move.l     #$0, $7805032.l
07874558  4ef907948474                 jmp        $7948474.l
0787455e  30bc0042                     move.w     #$42, (a0)
07874562  4e75                         rts

# Return receive buffer ownership: linked 0x078745a6, file 0x6f5a6
078745a6  22790799ea1c                 movea.l    $799ea1c.l, a1
078745ac  2149fffa                     move.l     a1, -$6(a0)
078745b0  337cfa120004                 move.w     #$fa12, $4(a1)
078745b6  2008                         move.l     a0, d0
078745b8  028000ffffff                 andi.l     #$ffffff, d0
078745be  4840                         swap       d0
078745c0  024000ff                     andi.w     #$ff, d0
078745c4  08c0000f                     bset.b     #$f, d0
078745c8  2280                         move.l     d0, (a1)
078745ca  b3f90799ea20                 cmpa.l     $799ea20.l, a1
078745d0  6708                         beq.b      $78745da
078745d2  50b90799ea1c                 addq.l     #$8, $799ea1c.l
078745d8  600a                         bra.b      $78745e4
078745da  23f90799ea140799ea1c         move.l     $799ea14.l, $799ea1c.l

# Transmit descriptor and demand: linked 0x07874bd0, file 0x6fbd0
07874bd0  363cffc4                     move.w     #$ffc4, d3
07874bd4  20790799ea2c                 movea.l    $799ea2c.l, a0
07874bda  240a                         move.l     a2, d2
07874bdc  028200ffffff                 andi.l     #$ffffff, d2
07874be2  4842                         swap       d2
07874be4  024200ff                     andi.w     #$ff, d2
07874be8  31430004                     move.w     d3, $4(a0)
07874bec  00428300                     ori.w      #$8300, d2
07874bf0  2082                         move.l     d2, (a0)
07874bf2  227c00300000                 movea.l    #$300000, a1
07874bf8  337c00000002                 move.w     #$0, $2(a1)
07874bfe  40c1                         move.w     sr, d1
07874c00  46fc2300                     move.w     #$2300, sr
07874c04  3411                         move.w     (a1), d2
07874c06  02420040                     andi.w     #$40, d2
07874c0a  00420008                     ori.w      #$8, d2
07874c0e  3282                         move.w     d2, (a1)
07874c10  46c1                         move.w     d1, sr
07874c12  b1f90799ea30                 cmpa.l     $799ea30.l, a0
07874c18  6708                         beq.b      $7874c22
07874c1a  50b90799ea2c                 addq.l     #$8, $799ea2c.l
07874c20  600a                         bra.b      $7874c2c
07874c22  23f90799ea240799ea2c         move.l     $799ea24.l, $799ea2c.l
07874c2c  4e75                         rts

# Interrupt setup, immediate and deferred handlers: linked 0x07874c86, file 0x6fc86
07874c86  48e700c0                     movem.l    a0-a1, -(a7)
07874c8a  41f90799ed48                 lea.l      $799ed48.l, a0
07874c90  20bc00300000                 move.l     #$300000, (a0)
07874c96  42a80008                     clr.l      $8(a0)
07874c9a  42a8000c                     clr.l      $c(a0)
07874c9e  217c000000020004             move.l     #$2, $4(a0)
07874ca6  43e80010                     lea.l      $10(a0), a1
07874caa  2289                         move.l     a1, (a1)
07874cac  237c07874d020004             move.l     #$7874d02, $4(a1)
07874cb4  317c006c0018                 move.w     #$6c, $18(a0)
07874cba  4e7a8801                     movec      vbr, a0
07874cbe  21bc07874cd001700000006c     move.l     #$7874cd0, $6c(a0, invalid.w)
07874cca  4cdf0300                     movem.l    (a7)+, a0-a1
07874cce  4e75                         rts
07874cd0  48e7f0e0                     movem.l    d0-d3/a0-a2, -(a7)
07874cd4  45f90799ed48                 lea.l      $799ed48.l, a2
07874cda  52aa0008                     addq.l     #$1, $8(a2)
07874cde  2252                         movea.l    (a2), a1
07874ce0  32bc0000                     move.w     #$0, (a1)
07874ce4  262a0004                     move.l     $4(a2), d3
07874ce8  45ea0010                     lea.l      $10(a2), a2
07874cec  4eb9078ecfbc                 jsr        $78ecfbc.l
07874cf2  4cdf070f                     movem.l    (a7)+, d0-d3/a0-a2
07874cf6  23fc00000010079ac5b0         move.l     #$10, $79ac5b0.l
07874d00  4e73                         rte
07874d02  45eafff0                     lea.l      -$10(a2), a2
07874d06  52aa000c                     addq.l     #$1, $c(a2)
07874d0a  2f0a                         move.l     a2, -(a7)
07874d0c  610a                         bsr.b      $7874d18
07874d0e  245f                         movea.l    (a7)+, a2
07874d10  2252                         movea.l    (a2), a1
07874d12  32bc0040                     move.w     #$40, (a1)
07874d16  4e75                         rts

# CSR0 status processing: linked 0x07874d18, file 0x6fd18
07874d18  48e70f1e                     movem.l    d4-d7/a3-a6, -(a7)
07874d1c  4280                         clr.l      d0
07874d1e  4281                         clr.l      d1
07874d20  207c00300000                 movea.l    #$300000, a0
07874d26  317c00000002                 move.w     #$0, $2(a0)
07874d2c  3010                         move.w     (a0), d0
07874d2e  08000002                     btst.b     #$2, d0
07874d32  670a                         beq.b      $7874d3e
07874d34  30390799ea34                 move.w     $799ea34.l, d0
07874d3a  00400004                     ori.w      #$4, d0
07874d3e  08000004                     btst.b     #$4, d0
07874d42  660c                         bne.b      $7874d50
07874d44  00400004                     ori.w      #$4, d0
07874d48  00400400                     ori.w      #$400, d0
07874d4c  00400200                     ori.w      #$200, d0
07874d50  3200                         move.w     d0, d1
07874d52  02010004                     andi.b     #$4, d1
07874d56  3081                         move.w     d1, (a0)
07874d58  0800000f                     btst.b     #$f, d0
07874d5c  67000092                     beq.w      $7874df0
07874d60  0800000b                     btst.b     #$b, d0
07874d64  6728                         beq.b      $7874d8e
07874d66  23fc07874d6607805028         move.l     #$7874d66, $7805028.l
07874d70  40f907805030                 move.w     sr, $7805030.l
07874d76  33fc021107805036             move.w     #$211, $7805036.l
07874d7e  23fc0000000007805032         move.l     #$0, $7805032.l
07874d88  4ef907948474                 jmp        $7948474.l
07874d8e  0800000c                     btst.b     #$c, d0
07874d92  6722                         beq.b      $7874db6
07874d94  30bc0004                     move.w     #$4, (a0)
07874d98  00400004                     ori.w      #$4, d0
07874d9c  00400400                     ori.w      #$400, d0
07874da0  00400200                     ori.w      #$200, d0
07874da4  52b90799eb4e                 addq.l     #$1, $799eb4e.l
07874daa  640a                         bcc.b      $7874db6
07874dac  23fc000000010799eb52         move.l     #$1, $799eb52.l
07874db6  0800000e                     btst.b     #$e, d0
07874dba  6712                         beq.b      $7874dce
07874dbc  52b90799eade                 addq.l     #$1, $799eade.l
07874dc2  640a                         bcc.b      $7874dce
07874dc4  23fc000000010799eae2         move.l     #$1, $799eae2.l
07874dce  0800000d                     btst.b     #$d, d0
07874dd2  671c                         beq.b      $7874df0
07874dd4  083900020799ea42             btst.b     #$2, $799ea42.l
07874ddc  6612                         bne.b      $7874df0
07874dde  52b90799eaee                 addq.l     #$1, $799eaee.l
07874de4  640a                         bcc.b      $7874df0
07874de6  23fc000000010799eaf2         move.l     #$1, $799eaf2.l
07874df0  0800000a                     btst.b     #$a, d0
07874df4  6704                         beq.b      $7874dfa
07874df6  61000024                     bsr.w      $7874e1c
07874dfa  08000009                     btst.b     #$9, d0
07874dfe  6704                         beq.b      $7874e04
07874e00  6100059e                     bsr.w      $78753a0
07874e04  08000002                     btst.b     #$2, d0
07874e08  670c                         beq.b      $7874e16
07874e0a  4eb90787437e                 jsr        $787437e.l
07874e10  4eb9078744ea                 jsr        $78744ea.l
07874e16  4cdf78f0                     movem.l    (a7)+, d4-d7/a3-a6
07874e1a  4e75                         rts

# Receive descriptor and DMA address processing: linked 0x07874e1c, file 0x6fe1c
07874e1c  2f00                         move.l     d0, -(a7)
07874e1e  4286                         clr.l      d6
07874e20  22790799ea18                 movea.l    $799ea18.l, a1
07874e26  2411                         move.l     (a1), d2
07874e28  0802000f                     btst.b     #$f, d2
07874e2c  66000472                     bne.w      $78752a0
07874e30  2602                         move.l     d2, d3
07874e32  024300ff                     andi.w     #$ff, d3
07874e36  4843                         swap       d3
07874e38  008307800000                 ori.l      #$7800000, d3
07874e3e  2443                         movea.l    d3, a2
07874e40  08020009                     btst.b     #$9, d2
07874e44  67000128                     beq.w      $7874f6e
07874e48  08020008                     btst.b     #$8, d2
07874e4c  6700010e                     beq.w      $7874f5c
07874e50  0802000e                     btst.b     #$e, d2
07874e54  67000132                     beq.w      $7874f88

# Multicast CRC hash and logical address filter: linked 0x07874a02, file 0x6fa02
07874a02  48e70c00                     movem.l    d4-d5, -(a7)
07874a06  43f907873e0c                 lea.l      $7873e0c.l, a1
07874a0c  7203                         moveq      #$3, d1
07874a0e  4259                         clr.w      (a1)+
07874a10  51c9fffc                     dbra       d1, $7874a0e
07874a14  7801                         moveq      #$1, d4
07874a16  7205                         moveq      #$5, d1
07874a18  7a08                         moveq      #$8, d5
07874a1a  45f907873e1c                 lea.l      $7873e1c.l, a2
07874a20  94c5                         suba.w     d5, a2
07874a22  6042                         bra.b      $7874a66
07874a24  d4c5                         adda.w     d5, a2
07874a26  4a52                         tst.w      (a2)
07874a28  673c                         beq.b      $7874a66
07874a2a  0c52ffff                     cmpi.w     #$ffff, (a2)
07874a2e  6736                         beq.b      $7874a66
07874a30  7606                         moveq      #$6, d3
07874a32  48e74020                     movem.l    d1/a2, -(a7)
07874a36  4eb907941aa0                 jsr        $7941aa0.l
07874a3c  4cdf0402                     movem.l    (a7)+, d1/a2
07874a40  4840                         swap       d0
07874a42  4680                         not.l      d0
07874a44  ed98                         rol.l      #$6, d0
07874a46  02800000003f                 andi.l     #$3f, d0
07874a4c  2400                         move.l     d0, d2
07874a4e  0202000f                     andi.b     #$f, d2
07874a52  02000030                     andi.b     #$30, d0
07874a56  e688                         lsr.l      #$3, d0
07874a58  7601                         moveq      #$1, d3
07874a5a  e56b                         lsl.w      d2, d3
07874a5c  43f907873e0c                 lea.l      $7873e0c.l, a1
07874a62  87710000                     or.w       d3, (a1, d0.w)
07874a66  51c9ffbc                     dbra       d1, $7874a24
07874a6a  7204                         moveq      #$4, d1
07874a6c  45f907873e54                 lea.l      $7873e54.l, a2
07874a72  7a0c                         moveq      #$c, d5
07874a74  94c5                         suba.w     d5, a2
07874a76  51ccffee                     dbra       d4, $7874a66
07874a7a  08b900030780500d             bclr.b     #$3, $780500d.l
07874a82  4cdf0030                     movem.l    (a7)+, d4-d5
07874a86  4e75                         rts

# Six-byte board identity read; MAC role still tentative: linked 0x079409e2, file 0x13b9e2
079409e2  40c1                         move.w     sr, d1
079409e4  46fc2600                     move.w     #$2600, sr
079409e8  43f900200000                 lea.l      $200000.l, a1
079409ee  7005                         moveq      #$5, d0
079409f0  14d1                         move.b     (a1), (a2)+
079409f2  5289                         addq.l     #$1, a1
079409f4  51c8fffa                     dbra       d0, $79409f0
079409f8  46c1                         move.w     d1, sr
079409fa  4e75                         rts
