// =====================================================================
// Turek-Hron FSI benchmark — FLUID domain mesh
// Target solver:  SU2  (incompressible Navier-Stokes, P1 triangles)
// Output:         fluid.su2  
// Coupling:       preCICE  → interface = "beam_wet"
// =====================================================================

SetFactory("OpenCASCADE");

// --------- 1. Parameters ----------
L  = 2.5;
H  = 0.41;
xC = 0.2;   yC = 0.2;
r  = 0.05;

xBl = xC;     
xBr = 0.6;
yBb = 0.19; 
yBt = 0.21;

// Mesh sizes 
lc_far   = 0.02;     
lc_wake  = 0.008;    
lc_near  = 0.003;    
lc_bl    = 0.001;    


// --------- 2. Build geometry ----------
Rectangle(1) = {0, 0, 0, L, H, 0};
Disk(2) = {xC, yC, 0, r};
Rectangle(3) = {xBl, yBb, 0, xBr-xBl, yBt-yBb};

// 유체 도메인에서 실린더와 빔 빼기
BooleanDifference(100) = { Surface{1}; Delete; }
                         { Surface{2, 3}; Delete; };

// [추가된 부분] Point B 생성 및 유체 도메인 경계에 임베딩(Fragment)
// 점을 (0.15, 0.2)에 생성한 뒤, 유체 면과 충돌시켜 실린더 테두리 선을 쪼갭니다.
Point(200) = {0.15, 0.2, 0, lc_bl};
Point(300) = {0.6, 0.2, 0, lc_bl};
//Point{200} In Curve{5};이거 안됨
//Point{300} In Curve{6};

BooleanFragments{ Surface{100}; Delete; }{ Point{200,300}; Delete; }
Coherence;

// Fragment 연산 이후 면 ID를 안전하게 탐색
s_fluid[] = Surface In BoundingBox{ -1e-6, -1e-6, -1e-6, L+1e-6, H+1e-6, 1e-6 };

// --------- 3. Identify boundaries by bounding box ----------
eps = 1e-6;

c_inlet[]  = Curve In BoundingBox{ -eps,   -eps, -eps,   eps,  H+eps, eps };
c_outlet[] = Curve In BoundingBox{ L-eps,  -eps, -eps, L+eps,  H+eps, eps };
c_bot[]    = Curve In BoundingBox{ -eps,   -eps, -eps, L+eps,    eps, eps };
c_top[]    = Curve In BoundingBox{ -eps,  H-eps, -eps, L+eps,  H+eps, eps };

// [핵심] Fragment로 인해 실린더 선이 분할되었지만, BoundingBox 덕분에 쪼개진 모든 곡선이 c_cyl_all에 안전하게 들어갑니다.
c_cyl_all[] = Curve In BoundingBox{ xC-r-eps, yC-r-eps, -eps, xC+r+eps, yC+r+eps,  eps };

c_beam_top[]   = Curve In BoundingBox{ xBl-eps, yBt-eps, -eps, xBr+eps, yBt+eps, eps };
c_beam_bot[]   = Curve In BoundingBox{ xBl-eps, yBb-eps, -eps, xBr+eps, yBb+eps, eps };
c_beam_right[] = Curve In BoundingBox{ xBr-eps, yBb-eps, -eps, xBr+eps, yBt+eps, eps };

// [추가된 부분] Point B를 나중에 SU2에서 그룹으로 쓰기 위해 식별해 둡니다.
p_B[] = Point In BoundingBox{ 0.15-eps, 0.2-eps, -eps, 0.15+eps, 0.2+eps, eps };
p_A[] = Point In BoundingBox{ 0.6-eps, 0.2-eps, -eps, 0.6+eps, 0.2+eps, eps };



// --------- 4. Mesh size fields ----------
Field[1] = Distance;
Field[1].CurvesList = { c_cyl_all[], c_beam_top[], c_beam_bot[], c_beam_right[] };
Field[1].Sampling = 400;

Field[2] = Threshold;
Field[2].InField  = 1;
Field[2].SizeMin  = lc_bl;
Field[2].SizeMax  = lc_far;
Field[2].DistMin  = 0.005;   
Field[2].DistMax  = 0.30;    

Field[3] = Threshold;
Field[3].InField  = 1;
Field[3].SizeMin  = lc_near;
Field[3].SizeMax  = lc_far;
Field[3].DistMin  = 0.02;
Field[3].DistMax  = 0.15;

Field[4] = Box;
Field[4].VIn  = lc_wake;
Field[4].VOut = lc_far;
Field[4].XMin = 0.25;  
Field[4].XMax = 1.5;
Field[4].YMin = 0.10;  Field[4].YMax = 0.30;
Field[4].Thickness = 0.05;

Field[10] = Min;
Field[10].FieldsList = { 2, 3, 4 };

Background Field = 10;

Mesh.MeshSizeFromPoints = 0;
Mesh.MeshSizeFromCurvature = 0;
Mesh.MeshSizeExtendFromBoundary = 0;

// --------- 5. Physical groups (= SU2 MARKER tags) ----------
Physical Curve("inlet")    = { c_inlet[]  };
Physical Curve("outlet")   = { c_outlet[] };
Physical Curve("wall_top") = { c_top[]    };
Physical Curve("wall_bot") = { c_bot[]    };
Physical Curve("cylinder") = { c_cyl_all[] };
Physical Curve("beam_wet") = { c_beam_top[], c_beam_bot[], c_beam_right[] };

Physical Surface("fluid")  = { s_fluid[0] };

// [추가된 부분] 유체 해석기(SU2 등)에서 압력 모니터링 프로브(Probe)로 쓸 수 있도록 이름 부여
Physical Point("point_B")  = { p_B[0] };
Physical Point("point_A")  = { p_A[0] };

// --------- 6. Mesh options ----------
Mesh.Algorithm    = 6;      
Mesh.ElementOrder = 1;      
Mesh.MshFileVersion = 2.2;  
Mesh.SaveAll = 0;