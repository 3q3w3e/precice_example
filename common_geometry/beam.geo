// =====================================================================
// Turek-Hron FSI benchmark — SOLID domain mesh
// Target solver:  Code_Aster  (2D plane strain, large deformation)
// Output:         beam.med  
// =====================================================================

SetFactory("OpenCASCADE");

// --------- 1. Parameters ----------
xC = 0.2; yC = 0.2; r = 0.05; 

xBl = xC;  
xBr = 0.6;
yBb = 0.19; 
yBt = 0.21;
h_beam = yBt - yBb;       
l_beam = xBr - xBl;       

lc_mid  = 0.0025;         
lc_end  = 0.0015;         

// --------- 2. Geometry ----------
Rectangle(1) = {xBl, yBb, 0, l_beam, h_beam, 0};
Disk(2) = {xC, yC, 0, r};

// 빔 형상 파내기 (오목한 왼쪽 면 생성)
BooleanDifference(10) = { Surface{1}; Delete; }{ Surface{2}; Delete; };

// Point A(팁 끝단 중심)를 위한 위치에 점(Point) 생성
Point(100) = {xBr, 0.5*(yBb+yBt), 0, lc_end};

// [핵심 해결책] OpenCASCADE에서는 점을 선에 '포함'시킬 수 없으므로,
// BooleanFragments 연산을 통해 면/선을 점(Point)으로 교차 분할(Split) 해버립니다.
// 이 연산을 거치면 오른쪽 테두리 선이 Point A를 기준으로 정확히 위아래 2개로 쪼개집니다.
BooleanFragments{ Surface{10}; Delete; }{ Point{100}; Delete; }

Coherence;

// --------- 3. Identify boundaries ----------
eps = 1e-6;

c_fixed[] = Curve In BoundingBox{ xC-eps, yBb-eps, -eps, xC+r+eps, yBt+eps, eps };

// [중요] Fragment 연산으로 오른쪽 선이 2개로 쪼개졌지만, 
// BoundingBox로 전체 영역을 탐색하므로 c_right 배열에 쪼개진 2개의 선이 모두 안전하게 저장됩니다!
c_right[] = Curve In BoundingBox{ xBr-eps, yBb-eps, -eps, xBr+eps, yBt+eps, eps };
c_top[]   = Curve In BoundingBox{ xC-eps, yBt-eps, -eps, xBr+eps, yBt+eps, eps };
c_bot[]   = Curve In BoundingBox{ xC-eps, yBb-eps, -eps, xBr+eps, yBb+eps, eps };

// Fragment 연산 후 면(Surface)과 점(Point)의 ID 번호가 무작위로 바뀔 수 있습니다.
// 따라서 하드코딩된 ID(예: 10번)를 쓰지 않고, 위치(BoundingBox)를 통해 확실하게 찾아냅니다.
s_beam[] = Surface In BoundingBox{ xBl-eps, yBb-eps, -eps, xBr+eps, yBt+eps, eps };
p_A[]    = Point In BoundingBox{ xBr-eps, 0.5*(yBb+yBt)-eps, -eps, xBr+eps, 0.5*(yBb+yBt)+eps, eps };


// --------- 4. Mesh size fields ----------
Field[1] = Distance;
Field[1].CurvesList = { c_fixed[], c_right[] };
Field[1].Sampling = 100;

Field[2] = Threshold;
Field[2].InField  = 1;
Field[2].SizeMin  = lc_end;
Field[2].SizeMax  = lc_mid;
Field[2].DistMin  = 0.005;
Field[2].DistMax  = 0.10;

Background Field = 2;

Mesh.MeshSizeFromPoints = 0;
Mesh.MeshSizeFromCurvature = 0;
Mesh.MeshSizeExtendFromBoundary = 0;

// --------- 5. Physical groups ----------
Physical Curve("beam_fixed") = { c_fixed[] };
Physical Curve("beam_wet")   = { c_top[], c_right[], c_bot[] };

// BoundingBox로 찾은 면과 점의 ID를 부여
Physical Surface("beam")     = { s_beam[0] };
Physical Point("point_A")    = { p_A[0] };

// --------- 6. Mesh options ----------
Mesh.Algorithm    = 6;      
Mesh.ElementOrder = 2;      
Mesh.SecondOrderIncomplete = 0;
Mesh.SecondOrderLinear     = 0;   
Mesh.MshFileVersion = 2.2;
Mesh.SaveAll = 0;