// =====================================================================
// Turek-Hron FSI benchmark -- FLUID domain block mesh with virtual C-grid
// =====================================================================
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
xCs = 0.325; // upstream cross-section station
xWt = 0.65;  // wake transition station
xWd = 1.0;  // downstream wake split station
xCt = 1.75;  // tail cross-section station
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
grid_convergence_scale = 1.0;

nx_inlet_manual           = 11;
nx_cgrid_arc_manual       = 7;
nx_xcs_inner_left_manual  = 7;
nx_xcs_inner_right_manual = 27;

n_radial_manual    = 5;
ny_lower_manual    = 11;
ny_upper_manual    = 12;
ny_tip_half_manual = 4;

// Wake controls.  These are left automatic so the downstream wake can stay
// smooth while the rest of the mesh is adjusted by direct node counts.
wake_cell_size_scale = 1.0;
wake_growth_strength = 1.5; // 0 uniform; 1 means outlet cell is about 2x xWd cell
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
Line(18) = {10, 182}; // beam bottom, reversed in the physical group
Line(21) = {20, 181}; // beam top
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

// C-grid radial connectors between real and virtual boundaries.
Line(61) = {40, 50};
Line(62) = {18, 52};
Line(63) = {8, 54};
Line(64) = {41, 56};

// Wake split lines.
Line(73) = {62, 60};
Line(77) = {63, 65};
Line(72) = {168, 170};
Line(85) = {21, 168};
Line(86) = {170, 11};
Line(92) = {168, 60};
Line(97) = {170, 63};
Line(210) = {207, 65};
Line(211) = {206, 62};
Line(212) = {168, 206};
Line(213) = {207, 170};
Line(214) = {180, 168};
Line(215) = {206, 185};
Line(216) = {184, 207};
Line(217) = {183, 170};
Line(178) = {60, 63};
Line(179) = {66, 67};
Line(195) = {65, 186};
Line(196) = {186, 6};
Line(197) = {63, 187};
Line(198) = {187, 66};
Line(199) = {60, 188};
Line(200) = {188, 67};
Line(201) = {62, 189};
Line(202) = {189, 28};
Line(203) = {186, 187};
Line(204) = {187, 188};
Line(205) = {188, 189};

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

// 5.1 Outer channel and wake blocks.
Curve Loop(101) = {1, 25, -17, -6};
Plane Surface(101) = {101};

Curve Loop(102) = {2, 3, 27, -56, -55, -25};
Plane Surface(102) = {102};

Curve Loop(103) = {4, -183, -58, -27};
Plane Surface(103) = {103};

Curve Loop(124) = {183, 216, 213, -217};
Plane Surface(124) = {124};

Curve Loop(105) = {7, 20, 53, 54, -17};
Plane Surface(105) = {105};

Curve Loop(106) = {85, 72, 86, 23, 24};
Plane Surface(106) = {106};

Curve Loop(107) = {8, 9, -26, -20};
Plane Surface(107) = {107};

Curve Loop(108) = {-52, -51, 28, -11, -10, -26};
Plane Surface(108) = {108};

Curve Loop(109) = {57, -180, -12, -28};
Plane Surface(109) = {109};

Curve Loop(125) = {180, 214, 212, 215};
Plane Surface(125) = {125};

Curve Loop(131) = {181, 192, 85, -214};
Plane Surface(131) = {131};

// Transition block from the merged near-wake block to the split wake.
Curve Loop(123) = {92, 178, -97, -72};
Plane Surface(123) = {123};

// 5.2 Inner C-grid blocks between real and virtual geometry.
Curve Loop(111) = {31, 32, 61, 51, 52, -62};
Plane Surface(111) = {111};

Curve Loop(112) = {-36, -35, 63, -54, -53, -62};
Plane Surface(112) = {112};

Curve Loop(113) = {-34, -38, 64, -56, -55, -63};
Plane Surface(113) = {113};

Curve Loop(114) = {-33, 18, 182, -58, -64};
Plane Surface(114) = {114};

Curve Loop(115) = {37, 21, -181, -57, -61};
Plane Surface(115) = {115};


Curve Loop(116) = {77, 195, 203, -197};
Plane Surface(116) = {116};

Curve Loop(128) = {196, 14, -198, -203};
Plane Surface(128) = {128};

Curve Loop(132) = {182, 217, 86, -194};
Plane Surface(132) = {132};

Curve Loop(118) = {178, 197, 204, -199};
Plane Surface(118) = {118};

Curve Loop(129) = {200, -179, -198, 204};
Plane Surface(129) = {129};

Curve Loop(120) = {92, -73, -211, -212};
Plane Surface(120) = {120};

Curve Loop(133) = {210, -77, -97, -213};
Plane Surface(133) = {133};

Curve Loop(122) = {199, 205, -201, 73};
Plane Surface(122) = {122};

Curve Loop(130) = {200, 16, -202, -205};
Plane Surface(130) = {130};

fluid_surfaces[] = {101, 102, 103, 105, 106, 107, 108, 109, 111, 112, 113, 114, 115, 116, 118, 120, 122, 123, 124, 125, 128, 129, 130, 131, 132, 133};
fluid_recombine_surfaces[] = {101, 102, 103, 105, 106, 107, 108, 109, 111, 112, 113, 114, 115, 116, 118, 120, 122, 123, 124, 125, 128, 129, 130, 131, 132, 133};

// =====================================================================
// 6. MESH COUNTS AND TRANSFINITE ASSIGNMENTS
// =====================================================================

// 6.1 Counts locked to the dependencies required by the transfinite topology.
// Non-wake counts are copied from the user block above.  A few linked counts
// are still derived so opposite sides of each transfinite surface stay equal.
mesh_scale = Max(0.000001, grid_convergence_scale);
target_wake_cell_size = 0.0125 * wake_cell_size_scale / mesh_scale;

nx_inlet = Max(3, Round((nx_inlet_manual - 1) * mesh_scale) + 1);
nx_cgrid_arc = Max(4, Round((nx_cgrid_arc_manual - 1) * mesh_scale) + 1);
nx_cgrid_mid = 2*nx_cgrid_arc - 1;

n_radial = Max(3, Round((n_radial_manual - 1) * mesh_scale) + 1);
nx_wake_near = n_radial;

ny_lower = Max(3, Round((ny_lower_manual - 1) * mesh_scale) + 1);
ny_upper = Max(3, Round((ny_upper_manual - 1) * mesh_scale) + 1);
ny_tip_half = Max(2, Round((ny_tip_half_manual - 1) * mesh_scale) + 1);
ny_beam_gap = 2*ny_tip_half - 1;

nx_xcs_inner_left = Max(3, Round((nx_xcs_inner_left_manual - 1) * mesh_scale) + 1);
nx_xcs_inner_right = Max(3, Round((nx_xcs_inner_right_manual - 1) * mesh_scale) + 1);
nx_xcs_outer_left = nx_xcs_inner_left + ny_beam_gap + n_radial - 2;

nx_wake_split = Max(3, Round((xWd - xWt) / target_wake_cell_size) + 1);

// One continuous downstream growth law on xWd -> L.  The two tail blocks are
// split at xCt only for topology; the cell-size progression is not reset.
wake_growth_rate = Log(1 + Max(0.000000001, wake_growth_strength)) / (L - xWd);
wake_decay_at_xCt = Exp(-wake_growth_rate * (xCt - xWd));
wake_decay_at_L = Exp(-wake_growth_rate * (L - xWd));
nx_tail_left = Max(3, Round((1 - wake_decay_at_xCt) / (target_wake_cell_size * wake_growth_rate)) + 1);
nx_tail_right = Max(3, Round((wake_decay_at_xCt - wake_decay_at_L) / (target_wake_cell_size * wake_growth_rate)) + 1);

wake_grow_left = Exp(wake_growth_rate * (xCt - xWd) / Max(1, nx_tail_left - 1));
wake_grow_right = Exp(wake_growth_rate * (L - xCt) / Max(1, nx_tail_right - 1));

// 6.2 Assign counts to curve families.
Transfinite Curve{1, 9, 17, 20} = nx_inlet;
Transfinite Curve{2, 3, 10, 11} = nx_cgrid_arc;
Transfinite Curve{4, 12, 57, 58} = nx_xcs_outer_left;
Transfinite Curve{18, 21} = nx_xcs_inner_left;
Transfinite Curve{192, 194, 214, 215, 216, 217} = nx_xcs_inner_right;
Transfinite Curve{85, 86} = nx_wake_near;
Transfinite Curve{92, 97, 210, 211} = nx_wake_split;
Transfinite Curve{195, 197, 199, 201} = nx_tail_left Using Progression wake_grow_left;
Transfinite Curve{196, 198, 200, 202} = nx_tail_right Using Progression wake_grow_right;

Transfinite Curve{6, 14, 25, 27, 77, 203, 213} = ny_lower;
Transfinite Curve{7} = nx_cgrid_mid;
Transfinite Curve{178, 179, 204} = ny_beam_gap;
Transfinite Curve{8, 16, 26, 28, 73, 205, 212} = ny_upper;
Transfinite Curve{180} = ny_upper;
Transfinite Curve{181, 182} = n_radial;
Transfinite Curve{183} = ny_lower;

Transfinite Curve{23, 24} = ny_tip_half;
Transfinite Curve{31, 32, 34, 35, 36, 38} = nx_cgrid_arc;
Transfinite Curve{33, 37} = ny_beam_gap + n_radial - 1;
Transfinite Curve{51, 52, 53, 54, 55, 56} = nx_cgrid_arc;
Transfinite Curve{72} = ny_beam_gap;
// Wall-normal clustering: cells are pulled toward the cylinder/beam wall.
Transfinite Curve{61, 62, 63, 64} = n_radial Using Progression wall_cluster;

Transfinite Surface{101} = {1, 2, 54, 7};
Transfinite Surface{102} = {2, 4, 56, 54};
Transfinite Surface{103} = {4, 184, 183, 56};
Transfinite Surface{124} = {184, 207, 170, 183};
Transfinite Surface{105} = {7, 17, 52, 54};
Transfinite Surface{107} = {17, 23, 24, 52};
Transfinite Surface{108} = {52, 50, 26, 24};
Transfinite Surface{109} = {50, 180, 185, 26};
Transfinite Surface{125} = {185, 180, 168, 206};

Transfinite Surface{111} = {18, 40, 50, 52};
Transfinite Surface{112} = {18, 8, 54, 52};
Transfinite Surface{113} = {8, 41, 56, 54};
Transfinite Surface{114} = {41, 182, 183, 56};
Transfinite Surface{115} = {40, 181, 180, 50};
Transfinite Surface{131} = {180, 181, 21, 168};
Transfinite Surface{116} = {63, 65, 186, 187};
Transfinite Surface{128} = {186, 6, 66, 187};
Transfinite Surface{118} = {60, 63, 187, 188};
Transfinite Surface{129} = {188, 67, 66, 187};
Transfinite Surface{120} = {168, 60, 62, 206};
Transfinite Surface{122} = {60, 188, 189, 62};
Transfinite Surface{130} = {188, 67, 28, 189};
Transfinite Surface{132} = {182, 183, 170, 11};
Transfinite Surface{133} = {207, 65, 63, 170};

// Near-wake block requested as a transfinite surface.
Transfinite Surface{106} = {21, 168, 170, 11};
Transfinite Surface{123} = {168, 60, 63, 170};

Recombine Surface{fluid_recombine_surfaces[]};

// =====================================================================
// 7. PHYSICAL GROUPS AND MESH OPTIONS
// =====================================================================

Physical Curve("inlet")    = {6, 7, 8};
Physical Curve("outlet")   = {14, 179, 16};
Physical Curve("wall_top") = {9, 10, 11, 12, 215, 211, 201, 202};
Physical Curve("wall_bot") = {1, 2, 3, 4, 216, 210, 195, 196};
Physical Curve("cylinder") = {31, 32, 37, 33, 38, 34, 35, 36};
Physical Curve("beam_wet") = {21, 24, 23, -18};

Physical Surface("fluid") = {fluid_surfaces[]};

Physical Point("point_B") = {14};
Physical Point("point_A") = {15};

Mesh.Algorithm = 5;
Mesh.RecombinationAlgorithm = 1;
Mesh.ElementOrder = 1;
Mesh.MshFileVersion = 2.2;
Mesh.SaveAll = 0;
