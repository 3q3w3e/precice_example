// Geometry-only version (mesh/topology stripped)
// ★ STEP 내보내기를 위해 OpenCASCADE 커널 사용 선언 ★
SetFactory("OpenCASCADE");

// =====================================================================
// 1. USER PARAMETERS
// =====================================================================

// 1.1 Physical geometry.
L  = 2.5;   // channel length
H  = 0.41;  // channel height
xC = 0.2;   // cylinder center x
yC = 0.2;   // cylinder center y
r  = 0.05;  // cylinder radius

xBr = 0.6;  // beam/cantilever end x
yBb = 0.19; // beam bottom y
yBt = 0.21; // beam top y

// 1.2 Virtual C-grid envelope and characteristic lengths.
r_virtual = 0.125;

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

// =====================================================================
// 3. POINTS (메쉬 크기 제어 변수 모두 제거됨)
// =====================================================================

// Fixed channel, beam, probes, and circle center.
Point(1)  = {0,   0,   0};
Point(3)  = {xC,  0,   0};
Point(5)  = {xBr, 0,   0};
Point(6)  = {L,   0,   0};

Point(11) = {xBr, yBb, 0};
Point(14) = {xC-r, yC, 0}; 
Point(15) = {xBr,  yC, 0};
Point(21) = {xBr, yBt, 0};

Point(23) = {0,   H, 0};
Point(25) = {xC,  H, 0};
Point(27) = {xBr, H, 0};
Point(28) = {L,   H, 0};

Point(29) = {xC, yC, 0}; 

// Real cylinder and beam interface points.
Point(40) = {x45,  y45,  0}; 
Point(18) = {x135, y135, 0};
Point(8)  = {x225, y225, 0}; 
Point(41) = {x315, y315, 0};

Point(19) = {xC,  yC+r, 0};
Point(20) = {xRi, yBt, 0};
Point(10) = {xRi, yBb, 0};
Point(9)  = {xC,  yC-r, 0};

// Virtual C-grid points.
Point(50) = {x45v,  y45v,  0};
Point(51) = {xC,    yC+r_virtual, 0};
Point(52) = {x135v, y135v, 0};
Point(53) = {xC-r_virtual, yC, 0};
Point(54) = {x225v, y225v, 0};
Point(55) = {xC,    yC-r_virtual, 0};
Point(56) = {x315v, y315v, 0};
Point(57) = {xBr, y45v,  0};
Point(58) = {xBr, y315v, 0};

Point(300) = {xRivTop, yBt, 0};
Point(301) = {xRivBot, yBb, 0};

// Projection points used by outer blocks.
Point(2)  = {x225v, 0, 0};
Point(4)  = {x315v, 0, 0};
Point(7)  = {0, y225v, 0};
Point(17) = {0, y135v, 0};
Point(24) = {x135v, H, 0};
Point(26) = {x45v,  H, 0};

// Outlet endpoints (Point 66, 67 삭제됨)
Point(234) = {L,   yBt, 0};
Point(235) = {L,   yBb, 0};

// =====================================================================
// 4. CURVES
// =====================================================================

// Outer boundaries.
Line(1)  = {1, 2};
Line(2)  = {2, 3};
Line(3)  = {3, 4};
Line(4)  = {4, 5};   
Line(6)  = {1, 7};
Line(7)  = {7, 17};
Line(8)  = {17, 23};
Line(9)  = {23, 24};
Line(10) = {24, 25};
Line(11) = {25, 26};
Line(12) = {26, 27}; 

// Outer block interfaces tied to the virtual C-grid.
Line(17) = {7, 54};
Line(20) = {17, 52};
Line(25) = {2, 54};
Line(26) = {52, 24};
Line(27) = {4, 56};
Line(28) = {50, 26};

// Real beam boundary.
Line(18) = {301, 11}; 
Line(21) = {300, 21}; 
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

Line(57) = {50, 57}; 
Line(58) = {56, 58}; 

Circle(300) = {50, 29, 300};
Circle(301) = {301, 29, 56};
Line(302) = {20, 300};
Line(303) = {10, 301};

// C-grid radial connectors between real and virtual boundaries.
Line(61) = {40, 50};
Line(62) = {18, 52};
Line(63) = {8, 54};
Line(64) = {41, 56};

// Beam trailing edge vertical splits.
Line(85)  = {21, 57};
Line(86)  = {58, 11};
Line(260) = {57, 27};
Line(263) = {5, 58};

// Continuous channel lines extending from xBr to L (Line 218, 219 삭제됨)
Line(265) = {5, 6};    // Bottom channel boundary
Line(262) = {27, 28};  // Top channel boundary
Line(222) = {21, 234}; // Beam top cut extension
Line(223) = {11, 235}; // Beam bottom cut extension

// Vertical exit plane boundaries (Point 66, 67 삭제로 인해 외곽선 재연결)
Line(14)  = {6, 235};   // Bottom channel to beam bottom cut
Line(248) = {235, 234}; // Beam thickness at exit
Line(16)  = {234, 28};  // Beam top cut to top channel