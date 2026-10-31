MNENG3 DTR/DSR evidence; file bias 0x07805000.
0x079423c4: 00 01 01 00 00 10 04 00

Function/range 0x7942282
07942282 2069000c                 movea.l $c(a1), a0
07942286 1018                     move.b (a0)+, d0
07942288 15401416                 move.b d0, $1416(a2)
0794228c 4600                     not.b d0
0794228e 15401417                 move.b d0, $1417(a2)
07942292 1018                     move.b (a0)+, d0
07942294 15401418                 move.b d0, $1418(a2)
07942298 4600                     not.b d0
0794229a 15401419                 move.b d0, $1419(a2)
0794229e 1018                     move.b (a0)+, d0
079422a0 1540141a                 move.b d0, $141a(a2)
079422a4 4600                     not.b d0
079422a6 1540141b                 move.b d0, $141b(a2)

Function/range 0x79442d4
079442d4 226a0008                 movea.l $8(a2), a1
079442d8 4a83                     tst.l d3
079442da 661c                     bne.b $79442f8
079442dc 0c2a00ff00d8             cmpi.b #$ff, $d8(a2)
079442e2 670a                     beq.b $79442ee
079442e4 137c00900002             move.b #$90, $2(a1)
079442ea 4a97                     tst.l (a7)
079442ec 4a97                     tst.l (a7)
079442ee 157c000013d0             move.b #$0, $13d0(a2)
079442f4 7001                     moveq #$1, d0
079442f6 4e75                     rts 
079442f8 0c2a00ff00d8             cmpi.b #$ff, $d8(a2)
079442fe 670a                     beq.b $794430a
07944300 137c00800002             move.b #$80, $2(a1)
07944306 4a97                     tst.l (a7)
07944308 4a97                     tst.l (a7)
0794430a 157c000113d0             move.b #$1, $13d0(a2)
07944310 7001                     moveq #$1, d0
07944312 4e75                     rts 

Function/range 0x7944318
07944318 256f000413ec             move.l $4(a7), $13ec(a2)
0794431e 254913e8                 move.l a1, $13e8(a2)
07944322 6718                     beq.b $794433c
07944324 206a0004                 movea.l $4(a2), a0
07944328 2250                     movea.l (a0), a1
0794432a 142a141a                 move.b $141a(a2), d2
0794432e 42aa13d4                 clr.l $13d4(a2)
07944332 85282898                 or.b d2, $2898(a0)
07944336 136828980008             move.b $2898(a0), $8(a1)
0794433c 206a0004                 movea.l $4(a2), a0
07944340 2250                     movea.l (a0), a1
07944342 142a141a                 move.b $141a(a2), d2
07944346 7000                     moveq #$0, d0
07944348 c429001a                 and.b $1a(a1), d2
0794434c 57c0                     seq.b d0
0794434e 4400                     neg.b d0
07944350 4e75                     rts 

Function/range 0x7943e24
07943e24 7000                     moveq #$0, d0
07943e26 25400014                 move.l d0, $14(a2)
07943e2a 80aa0054                 or.l $54(a2), d0
07943e2e 25400034                 move.l d0, $34(a2)
07943e32 157c00ff1119             move.b #$ff, $1119(a2)
07943e38 226a0004                 movea.l $4(a2), a1
07943e3c 2051                     movea.l (a1), a0
07943e3e 102a141b                 move.b $141b(a2), d0
07943e42 c1292898                 and.b d0, $2898(a1)
07943e46 116928980008             move.b $2898(a1), $8(a0)
07943e4c 226a0008                 movea.l $8(a2), a1
07943e50 4a29fffe                 tst.b -$2(a1)
07943e54 08e90004fffe             bset.b #$4, -$2(a1)
07943e5a 6000ff4c                 bra.w $7943da8

Function/range 0x7945300
07945300 48e76060                 movem.l d1-d2/a1-a2, -(a7)
07945304 45f8f0c4                 lea.l $f0c4.w, a2
07945308 43f90040001a             lea.l $40001a.l, a1
0794530e 7420                     moveq #$20, d2
07945310 7203                     moveq #$3, d1
07945312 1611                     move.b (a1), d3
07945314 871a                     or.b d3, (a2)+
07945316 c71a                     and.b d3, (a2)+
07945318 d2c2                     adda.w d2, a1
0794531a 51c9fff6                 dbra d1, $7945312
0794531e 4cdf0606                 movem.l (a7)+, d1-d2/a1-a2
07945322 261f                     move.l (a7)+, d3
07945324 4e75                     rts 
