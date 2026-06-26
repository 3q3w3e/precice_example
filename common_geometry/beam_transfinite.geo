// =====================================================================
// Turek-Hron FSI benchmark — SOLID domain mesh (구조격자 버전)
// Target solver:  Code_Aster  (2D plane strain, large deformation)
// Output:         beam.med
//
// 변경점:
//   - OpenCASCADE Boolean 제거 -> built-in 커널로 4변(quad) 형상 직접 정의
//   - 왼쪽 고정단은 실린더 오목 원호(곡선) 유지
//   - Transfinite 로 점 개수 직접 지정 (길이 120 x 높이 16, 균일)
//   - 사각형(quad) 정렬격자 출력 (Recombine)
// =====================================================================

// --------- 1. Parameters ----------
xC = 0.2; yC = 0.2; r = 0.05;     // 실린더 중심/반지름

xBr = 0.6;                        // 빔 오른쪽 끝(팁)
yBb = 0.19;                       // 빔 아래 변 y
yBt = 0.21;                       // 빔 위 변 y

// 빔 위/아래 변이 실린더와 만나는 x (좌측 곡선 시작점)
//   (x-xC)^2 + (y-yC)^2 = r^2  ->  x = xC + sqrt(r^2 - (y-yC)^2)
xL_top = xC + Sqrt(r^2 - (yBt - yC)^2);   // = 0.24899...
xL_bot = xC + Sqrt(r^2 - (yBb - yC)^2);   // = 0.24899... (대칭)

// --------- 점 개수 (여기 숫자만 바꾸면 됩니다) ----------
N_len = 120;   // 길이 방향 점 개수 (빔을 따라)
N_hgt = 16;    // 높이(두께) 방향 점 개수

// --------- 2. Geometry (4 corners + arc center) ----------
// 코너 점 (반시계 방향): 좌하 -> 우하 -> 우상 -> 좌상
Point(1) = {xL_bot, yBb, 0};   // 좌하 (곡선 아래 끝)
Point(2) = {xBr,    yBb, 0};   // 우하
Point(3) = {xBr,    yBt, 0};   // 우상
Point(4) = {xL_top, yBt, 0};   // 좌상 (곡선 위 끝)

// 실린더 중심점 (원호 정의용)
Point(5) = {xC, yC, 0};

// --------- 3. Curves ----------
Line(1)   = {1, 2};            // 아래 변 (직선)
Line(2)   = {2, 3};            // 오른쪽 변 (직선, 팁/wet)
Line(3)   = {3, 4};            // 위 변 (직선)
Circle(4) = {4, 5, 1};         // 왼쪽 변 (실린더 원호, 고정단) — 4에서 5(중심) 기준으로 1까지

// --------- 4. Surface ----------
Curve Loop(1) = {1, 2, 3, 4};
Plane Surface(1) = {1};

// --------- 5. Transfinite (점 개수 직접 지정) ----------
// 마주보는 변끼리 점 개수를 맞춰야 정렬격자가 만들어집니다.
//   길이 방향: 아래(1), 위(3)
//   높이 방향: 오른쪽(2), 왼쪽 원호(4)
Transfinite Curve{1, 3} = N_len;          // 길이 방향, 균일
Transfinite Curve{2, 4} = N_hgt;          // 높이 방향, 균일

Transfinite Surface{1} = {1, 2, 3, 4};    // 네 코너 지정
Recombine Surface{1};                      // 삼각형 -> 사각형(quad) 결합

// --------- 6. Physical groups ----------
// 고정단(원호) / wet 경계(위+오른쪽+아래) / 면 / 팁 점 A
Physical Curve("beam_fixed") = {4};
Physical Curve("beam_wet")   = {1, 2, 3};
Physical Surface("beam")     = {1};

// 팁 끝단 중심 Point A (오른쪽 변 중앙). 별도 점으로 표시하려면 아래 사용.
// 정렬격자에서는 격자점이 자동으로 그 위치에 생기므로 보통 불필요하지만,
// Physical Point 가 필요하면 오른쪽 변을 분할해야 합니다(요청 시 추가).

// --------- 7. Mesh options ----------
Mesh.ElementOrder = 2;        // 2차 요소 (기존과 동일)
Mesh.SecondOrderIncomplete = 0;
Mesh.SecondOrderLinear     = 0;
Mesh.MshFileVersion = 2.2;
Mesh.SaveAll = 0;

// 구조격자이므로 size field/curvature 기반 크기 제어는 끔
Mesh.MeshSizeFromPoints = 0;
Mesh.MeshSizeFromCurvature = 0;
Mesh.MeshSizeExtendFromBoundary = 0;
