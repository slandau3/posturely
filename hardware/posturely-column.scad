// Posturely slim-column concept. Measure purchased parts before STL export.
$fn = 48;

part = "assembly"; // "body", "rear_panel", or "assembly"
column_height = 180;
column_width = 65;
column_depth = 72;
wall = 2.4;
corner_radius = 4;
panel_thickness = 2.4;

camera_width = 18;
camera_height = 12;
camera_z = 151;
diagnostic_diameter = 5;
diagnostic_z = [112, 86, 60];
monitor_diameter = 3;
button_diameter = 8;
usb_width = 14;
usb_height = 8;
ballast_width = 48;
ballast_depth = 48;
ballast_height = 7;

module rounded_box(size, radius) {
    hull() {
        for (x = [radius, size[0] - radius])
            for (y = [radius, size[1] - radius])
                translate([x, y, 0])
                    cylinder(h = size[2], r = radius);
    }
}

module camera_cutout() {
    translate([(column_width-camera_width)/2, -1, camera_z])
        cube([camera_width, wall+2, camera_height]);
}

module diagnostic_apertures() {
    for (z = diagnostic_z)
        translate([column_width/2, -1, z])
            rotate([-90, 0, 0])
                cylinder(h = wall+2, d = diagnostic_diameter);
}

module monitor_aperture() {
    translate([column_width/2, -1, 26])
        rotate([-90, 0, 0])
            cylinder(h = wall+2, d = monitor_diameter);
}

module button_cutout() {
    translate([column_width/2, -1, 39])
        rotate([-90, 0, 0])
            cylinder(h = wall+2, d = button_diameter);
}

module usb_c_cutout() {
    translate([(column_width-usb_width)/2, column_depth-wall-1, 12])
        cube([usb_width, wall+2, usb_height]);
}

module ventilation() {
    for (x = [15:7:50])
        translate([x, column_depth-wall-1, 105])
            cube([3, wall+2, 32]);
}

module ballast_pocket() {
    translate([(column_width-ballast_width)/2,
               (column_depth-ballast_depth)/2, wall])
        cube([ballast_width, ballast_depth, ballast_height]);
}

module body() {
    difference() {
        rounded_box([column_width, column_depth, column_height], corner_radius);
        translate([wall, wall, wall])
            rounded_box([column_width-2*wall,
                         column_depth-2*wall,
                         column_height], corner_radius-wall/2);
        camera_cutout();
        diagnostic_apertures();
        monitor_aperture();
        button_cutout();
        usb_c_cutout();
        ventilation();
        ballast_pocket();
        translate([wall+3, column_depth-wall-1, 18])
            cube([column_width-2*wall-6, wall+2, column_height-36]);
    }
    light_barriers();
}

module light_barriers() {
    for (z = diagnostic_z)
        translate([column_width/2-6, wall, z-6])
            cube([12, 10, 1.4]);
}

module rear_panel() {
    translate([wall+3, 0, 18])
        cube([column_width-2*wall-6, panel_thickness, column_height-36]);
}

if (part == "body")
    body();
else if (part == "rear_panel")
    rear_panel();
else {
    body();
    translate([0, column_depth-panel_thickness, 0])
        rear_panel();
}
