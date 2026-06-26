// Geometry-only version (mesh/topology stripped)
// Auto-generated from fluid_grid.geo
// Uses Gmsh built-in kernel; export STEP/IGES via Gmsh Python API.
//
// This is a copy of fluid_block.geo.  The real cylinder/beam boundary is
// unchanged, but a larger virtual circle and a thicker virtual cantilever
// are used as C-grid block interfaces.

// =====================================================================
// 1. USER PARAMETERS
// =====================================================================
//
// Edit this block for ordinary geometry and mesh studies.  The sections
// below are derived construction details and should only need changes when
// the block topology itself is redesigned.

// 1.1 Physical geometry.
L  = 2.5;   // channel length
H  = 0.41;  // channel height
xC = 0.2;   // cylinder center x
yC = 0.2;   // cylinder center y
r  = 0.05;  // cylinder radius

xBr = 0.6;  // beam/cantilever end x
yBb = 0.19; // beam bottom y
yBt = 0.21; // beam top y

// 1.2 Manual topology stations.
xCs = 0.4; // upstream cross-section station
xWt = 0.75;  // wake transition station
xWd = 1.35;  // downstream wake split station
xCt = 1.95;  // tail cross-section station
tap = 0.025;

// 1.3 Virtual C-grid envelope and characteristic lengths.
r_virtual = 0.125;
lc_far = 0.04;
lc_bl  = 0.002;

// 1.4 Structured mesh controls.
// Counts are node counts on transfinite curves.  The wake resolution keeps the
// automatic growth law below; the other block families are direct manual knobs.
// Set grid_convergence_scale after choosing the manual ratios: 1.0 keeps the
// listed counts, values above 1.0 refine, and values below 1.0 coarsen.
grid_convergence_scale = 2.0;

nx_inlet_manual           = 11;
nx_cgrid_arc_manual       = 7;
nx_xcs_inner_left_manual  = 15;
nx_xcs_inner_right_manual = 40;
nx_xbr_xwt_manual         = 12;

n_radial_manual    = 30;
ny_lower_manual    = 8;
ny_upper_manual    = 8;
ny_tip_half_manual = 10;

// Wake controls.  These are left automatic so the downstream wake can stay
// smooth while the rest of the mesh is adjusted by direct node counts.
wake_cell_size_scale = 1.0;
wake_growth_strength = 1.75; // 0 uniform; 1 means outlet cell is about 2x xWd cell
wall_cluster = 1.05;        // wall-normal clustering toward cylinder/beam surfaces

// =====================================================================
// 2. DERIVED GEOMETRY
// =====================================================================

xRi = xC + Sqrt(r*r - (yBt-yC)*(yBt-yC));

d45 = r / Sqrt(2);
x45  = xC + d45; y45  = yC + d45;
x135 = xC - d45; y135 = yC + d45;
x225 = xC - d45; y225 = yC - d45;
x315 = xC + d45; y315 = yC - d45;

d45v = r_virtual / Sqrt(2);
x45v  = xC + d45v; y45v  = yC + d45v;
x135v = xC - d45v; y135v = yC + d45v;
x225v = xC - d45v; y225v = yC - d45v;
x315v = xC + d45v; y315v = yC - d45v;

xRivTop = xC + Sqrt(r_virtual*r_virtual - (yBt-yC)*(yBt-yC));
xRivBot = xC + Sqrt(r_virtual*r_virtual - (yBb-yC)*(yBb-yC));

// Fixed channel, beam, probes, and circle center.
Point(1)  = {0,   0,   0, lc_far};
Point(3)  = {xC,  0,   0, lc_far};
Point(5)  = {xBr, 0,   0, lc_far};
Point(6)  = {L,   0,   0, lc_far};

Point(11) = {xBr, yBb, 0, lc_bl};
Point(14) = {xC-r, yC, 0, lc_bl}; // point_B
Point(15) = {xBr,  yC, 0, lc_bl}; // point_A
Point(21) = {xBr, yBt, 0, lc_bl};

Point(23) = {0,   H, 0, lc_far};
Point(25) = {xC,  H, 0, lc_far};
Point(27) = {xBr, H, 0, lc_far};
Point(28) = {L,   H, 0, lc_far};

Point(29) = {xC, yC, 0, lc_bl}; // circle center

// =====================================================================
// 3. POINTS
// =====================================================================

// Real cylinder and beam interface points.
Point(40) = {x45,  y45,  0, lc_bl}; // real 45 deg
Point(18) = {x135, y135, 0, lc_bl}; // real 135 deg
Point(8)  = {x225, y225, 0, lc_bl}; // real 225 deg
Point(41) = {x315, y315, 0, lc_bl}; // real 315 deg

Point(19) = {xC,  yC+r, 0, lc_bl};
Point(20) = {xRi, yBt, 0, lc_bl};
Point(10) = {xRi, yBb, 0, lc_bl};
Point(9)  = {xC,  yC-r, 0, lc_bl};

// Virtual C-grid points.  These replace 8/18/40/41 as the outer block
// corners: 54/52/50/56 are the virtual 225/135/45/315 degree points.
Point(50) = {x45v,  y45v,  0, lc_far};
Point(51) = {xC,    yC+r_virtual, 0, lc_far};
Point(52) = {x135v, y135v, 0, lc_far};
Point(53) = {xC-r_virtual, yC, 0, lc_far};
Point(54) = {x225v, y225v, 0, lc_far};
Point(55) = {xC,    yC-r_virtual, 0, lc_far};
Point(56) = {x315v, y315v, 0, lc_far};

Point(57) = {xBr, y45v,  0, lc_far};
Point(58) = {xBr, y315v, 0, lc_far};

Point(300) = {xRivTop, yBt, 0, lc_far};
Point(301) = {xRivBot, yBb, 0, lc_far};

// Projection points used by outer blocks.
Point(2)  = {x225v, 0, 0, lc_far};
Point(4)  = {x315v, 0, 0, lc_far};
Point(7)  = {0, y225v, 0, lc_far};
Point(17) = {0, y135v, 0, lc_far};
Point(24) = {x135v, H, 0, lc_far};
Point(26) = {x45v,  H, 0, lc_far};

// Wake split points copied from fluid_block_virtual.geo.
Point(60) = {xWd, y45v + tap, 0, lc_far};
Point(62) = {xWd, H,    0, lc_far};

Point(63) = {xWd, y315v- tap, 0, lc_far};
Point(65) = {xWd, 0,     0, lc_far};

// Outlet endpoints for the downstream wake split.
Point(66) = {L, y315v-2*tap, 0, lc_far};
Point(67) = {L, y45v+2*tap,  0, lc_far};

// Wake transition points.
Point(168) = {xWt, y45v,  0, lc_far};
Point(170) = {xWt, y315v, 0, lc_far};
Point(206) = {xWt, H,     0, lc_far};
Point(207) = {xWt, 0,     0, lc_far};

// Cut points at xWt aligned with the beam top/bottom, used to split the
// near-wake block 106 into three structured bands (upper / tip / lower).
Point(220) = {xWt, yBt, 0, lc_far};
Point(221) = {xWt, yBb, 0, lc_far};

// Method A: continue the beam-height cut through the whole middle wake band so
// every downstream block is structured.  Top cut at yBt, bottom cut at yBb.
Point(230) = {xWd, yBt, 0, lc_far};
Point(231) = {xWd, yBb, 0, lc_far};
Point(232) = {xCt, yBt, 0, lc_far};
Point(233) = {xCt, yBb, 0, lc_far};
Point(234) = {L,   yBt, 0, lc_far};
Point(235) = {L,   yBb, 0, lc_far};

// Cross-section points at x = 0.45.
Point(184) = {xCs, 0,     0, lc_far};
Point(185) = {xCs, H,     0, lc_far};
Point(180) = {xCs, y45v,  0, lc_far};
Point(181) = {xCs, yBt,   0, lc_far};
Point(182) = {xCs, yBb,   0, lc_far};
Point(183) = {xCs, y315v, 0, lc_far};

// Cross-section points at x = 1.5.
Point(186) = {xCt, 0,     0, lc_far};
Point(187) = {xCt, y315v-2*tap, 0, lc_far};
Point(188) = {xCt, y45v+2*tap,  0, lc_far};
Point(189) = {xCt, H,     0, lc_far};

// =====================================================================
// 4. CURVES
// =====================================================================

// Outer boundaries.
Line(1)  = {1, 2};
Line(2)  = {2, 3};
Line(3)  = {3, 4};
Line(4)  = {4, 184};

Line(6) = {1, 7};
Line(7) = {7, 17};
Line(8) = {17, 23};

Line(9)  = {23, 24};
Line(10) = {24, 25};
Line(11) = {25, 26};
Line(12) = {26, 185};

Line(14) = {6, 66};
Line(16) = {67, 28};

// Outer block interfaces tied to the virtual C-grid, not the real circle.
Line(17) = {7, 54};
Line(20) = {17, 52};
Line(25) = {2, 54};
Line(26) = {52, 24};
Line(27) = {4, 56};
Line(28) = {50, 26};

// Real beam boundary.
Line(18) = {301, 182}; // beam bottom, reversed in the physical group
Line(21) = {300, 181}; // beam top
Line(23) = {11, 15};
Line(24) = {15, 21};

// Real cylinder boundary.
Circle(31) = {18, 29, 19};
Circle(32) = {19, 29, 40};
Circle(37) = {40, 29, 20};
Circle(33) = {10, 29, 41};
Circle(38) = {41, 29, 9};
Circle(34) = {9, 29, 8};
Circle(35) = {8, 29, 14};
Circle(36) = {14, 29, 18};

// Virtual larger circle and virtual thicker cantilever envelope.
Circle(51) = {50, 29, 51};
Circle(52) = {51, 29, 52};
Circle(53) = {52, 29, 53};
Circle(54) = {53, 29, 54};
Circle(55) = {54, 29, 55};
Circle(56) = {55, 29, 56};

Line(57) = {50, 180};
Line(58) = {56, 183};

Circle(300) = {50, 29, 300};
Circle(301) = {301, 29, 56};
Line(302) = {20, 300};
Line(303) = {10, 301};

// C-grid radial connectors between real and virtual boundaries.
Line(61) = {40, 50};
Line(62) = {18, 52};
Line(63) = {8, 54};
Line(64) = {41, 56};

// Wake split lines.
Line(73) = {62, 60};
Line(77) = {63, 65};
Line(72) = {168, 220};
Line(224) = {220, 221};
Line(225) = {221, 170};
Line(222) = {21, 220};
Line(223) = {11, 221};
Line(85) = {21, 57};
Line(86) = {58, 11};
Line(92) = {168, 60};
Line(97) = {170, 63};
Line(210) = {207, 65};
Line(211) = {206, 62};
Line(212) = {168, 206};
Line(213) = {207, 170};
Line(214) = {180, 57};
Line(218) = {57, 168};
Line(260) = {57, 27};
Line(261) = {185, 27};
Line(262) = {27, 206};
Line(263) = {5, 58};
Line(264) = {184, 5};
Line(265) = {5, 207};
Line(217) = {183, 58};
Line(219) = {58, 170};
// Method A: vertical wake-station boundaries split at the beam-height cut.
// xWd: 60-230-231-63   xCt(187-188 side): 187-233-232-188   L: 66-235-234-67
Line(250) = {60, 230};
Line(251) = {231, 63};
Line(252) = {187, 233};
Line(253) = {232, 188};
Line(254) = {66, 235};
Line(255) = {234, 67};
Line(195) = {65, 186};
Line(196) = {186, 6};
Line(197) = {63, 187};
Line(198) = {187, 66};
Line(199) = {60, 188};
Line(200) = {188, 67};
Line(201) = {62, 189};
Line(202) = {189, 28};
Line(203) = {186, 187};
Line(205) = {188, 189};

// Method A: beam-height cut lines continued downstream (top yBt, bottom yBb)
// and the vertical band dividers at each station.
Line(240) = {220, 230};
Line(241) = {230, 232};
Line(242) = {232, 234};
Line(243) = {221, 231};
Line(244) = {231, 233};
Line(245) = {233, 235};
Line(246) = {230, 231};
Line(247) = {232, 233};
Line(248) = {234, 235};

// Cross-section lines at x = 0.45.
Line(180) = {185, 180};
Line(181) = {180, 181};
Line(182) = {182, 183};
Line(183) = {183, 184};

// Split horizontal lines through the x = 0.45 cross-section.
Line(192) = {181, 21};
Line(194) = {182, 11};

// =====================================================================
// 5. SURFACES
// =====================================================================
// (surface definitions intentionally omitted in geometry-only version)

// 5.1 Outer channel and wake blocks.



// 5.2 Inner C-grid blocks between real and virtual geometry.


