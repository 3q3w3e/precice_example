function plot_ux_uy(csv_file, out_png)
%PLOT_UX_UY Plot x/y displacement histories from a solid_only CSV file.
%
% Usage:
%   plot_ux_uy
%   plot_ux_uy("solid_only.csv")
%   plot_ux_uy("solid_only.csv", "ux_uy.png")

if nargin < 1 || strlength(string(csv_file)) == 0
    csv_file = "solid_only.csv";
end

if nargin < 2
    out_png = "";
end

T = readtable(csv_file);

required = ["time", "ux", "uy"];
missing = required(~ismember(required, string(T.Properties.VariableNames)));
if ~isempty(missing)
    error("Missing required column(s): %s", strjoin(missing, ", "));
end

figure("Color", "w");

subplot(2, 1, 1);
plot(T.time, T.ux, "LineWidth", 1.4);
grid on;
xlabel("time [s]");
ylabel("u_x [m]");
title("X displacement");

subplot(2, 1, 2);
plot(T.time, T.uy, "LineWidth", 1.4);
grid on;
xlabel("time [s]");
ylabel("u_y [m]");
title("Y displacement");

if strlength(string(out_png)) > 0
    exportgraphics(gcf, out_png, "Resolution", 200);
end
end
