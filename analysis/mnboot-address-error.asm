MNBOOT.SYS candidate mapping: 512-byte wrapper, payload provisionally based at zero.
This is DS90M+ reference code, NOT a verified 90TL ROM.

Range 0x408
00000408 46fc2700                 move.w #$2700, sr
0000040c 48f90007078035e0         movem.l d0-d2, $78035e0.l
00000414 302f0016                 move.w $16(a7), d0
00000418 3200                     move.w d0, d1
0000041a 0241c3c0                 andi.w #$c3c0, d1
0000041e 0c410200                 cmpi.w #$200, d1
00000422 6646                     bne.b $46a
00000424 242f0008                 move.l $8(a7), d2
00000428 c588                     exg.l d2, a0
0000042a 3200                     move.w d0, d1
0000042c 02410018                 andi.w #$18, d1
00000430 6708                     beq.b $43a
00000432 0c410010                 cmpi.w #$10, d1
00000436 670a                     beq.b $442
00000438 603a                     bra.b $474
0000043a 10ef000c                 move.b $c(a7), (a0)+
0000043e 10ef000d                 move.b $d(a7), (a0)+
00000442 10ef000e                 move.b $e(a7), (a0)+
00000446 10ef000f                 move.b $f(a7), (a0)+
0000044a c588                     exg.l d2, a0
0000044c 52b907803624             addq.l #$1, $7803624.l
00000452 0800000c                 btst.b #$c, d0
00000456 6636                     bne.b $48e
00000458 08800009                 bclr.b #$9, d0
0000045c 3f400016                 move.w d0, $16(a7)
00000460 4cf90007078035e0         movem.l $78035e0.l, d0-d2
00000468 4e73                     rte 
0000046a 3200                     move.w d0, d1
0000046c 0241d380                 andi.w #$d380, d1
00000470 6700044e                 beq.w $8c0
00000474 4cf90007078035e0         movem.l $78035e0.l, d0-d2
0000047c 598f                     subq.l #$4, a7
0000047e 2f08                     move.l a0, -(a7)
00000480 4e7a8801                 movec vbr, a0
00000484 2f6800080004             move.l $8(a0), $4(a7)
0000048a 205f                     movea.l (a7)+, a0
0000048c 4e75                     rts 
0000048e 4cf90007078035e0         movem.l $78035e0.l, d0-d2
00000496 2f6f00100014             move.l $10(a7), $14(a7)
0000049c 3f7c20240012             move.w #$2024, $12(a7)
000004a2 2f6f0002000e             move.l $2(a7), $e(a7)
000004a8 3f57000c                 move.w (a7), $c(a7)
000004ac defc0008                 adda.w #$8, a7
000004b0 2f08                     move.l a0, -(a7)
000004b2 4e7a8801                 movec vbr, a0
000004b6 2f6800240004             move.l $24(a0), $4(a7)
000004bc 205f                     movea.l (a7)+, a0
000004be 4e75                     rts 

Range 0x8c0
000008c0 48f97ff8078035ec         movem.l d3-d7/a0-a6, $78035ec.l
000008c8 41ef0018                 lea.l $18(a7), a0
000008cc 23c80780361c             move.l a0, $780361c.l
000008d2 3e1f                     move.w (a7)+, d7
000008d4 245f                     movea.l (a7)+, a2
000008d6 23ca07803620             move.l a2, $7803620.l
000008dc 2e48                     movea.l a0, a7
000008de 3c1a                     move.w (a2)+, d6
000008e0 3006                     move.w d6, d0
000008e2 ec48                     lsr.w #$6, d0
000008e4 7200                     moveq #$0, d1
000008e6 123b0120fbd8             move.b $fbd8(a16, d0.w), d1
000008ec 4dfb166c                 lea.l $95a(pc, d1.w), a6
000008f0 204e                     movea.l a6, a0
000008f2 d0de                     adda.w (a6)+, a0
000008f4 4ed0                     jmp (a0)
000008f6 42c0                     move.w ccr, d0
000008f8 1e00                     move.b d0, d7
000008fa e19c                     rol.l #$8, d4
000008fc 18c4                     move.b d4, (a4)+
000008fe e19c                     rol.l #$8, d4
00000900 18c4                     move.b d4, (a4)+
00000902 e19c                     rol.l #$8, d4
00000904 18c4                     move.b d4, (a4)+
00000906 e19c                     rol.l #$8, d4
00000908 18c4                     move.b d4, (a4)+
0000090a 600c                     bra.b $918
0000090c 42c0                     move.w ccr, d0
0000090e 1e00                     move.b d0, d7
00000910 e15c                     rol.w #$8, d4
00000912 18c4                     move.b d4, (a4)+
00000914 e15c                     rol.w #$8, d4
00000916 18c4                     move.b d4, (a4)+
00000918 2e790780361c             movea.l $780361c.l, a7
0000091e 0807000f                 btst.b #$f, d7
00000922 6616                     bne.b $93a
00000924 4267                     clr.w -(a7)
00000926 2f0a                     move.l a2, -(a7)
00000928 3f07                     move.w d7, -(a7)
0000092a 4cf97fff078035e0         movem.l $78035e0.l, d0-d7/a0-a6
00000932 4e73                     rte 
00000934 42c0                     move.w ccr, d0
00000936 1e00                     move.b d0, d7
00000938 60de                     bra.b $918
0000093a 2f3907803620             move.l $7803620.l, -(a7)
00000940 3f3c2024                 move.w #$2024, -(a7)
00000944 2f0a                     move.l a2, -(a7)
00000946 3f07                     move.w d7, -(a7)
00000948 4e7a8801                 movec vbr, a0
0000094c 2f280024                 move.l $24(a0), -(a7)
00000950 4cf97fff078035e0         movem.l $78035e0.l, d0-d7/a0-a6
00000958 4e75                     rts 
