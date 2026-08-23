import 'package:flutter/material.dart';
import 'screens/report_list_screen.dart';

/// Smart Graffiti Management — mobile app entrypoint.
///
/// This is a skeleton: two screens (capture/submit + list) wired to a
/// ReportService that talks to the backend skeleton. Styling, error states,
/// and offline handling are intentionally minimal — build these out as the
/// team progresses.
void main() {
  runApp(const SmartGraffitiApp());
}

class SmartGraffitiApp extends StatelessWidget {
  const SmartGraffitiApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Smart Graffiti Management',
      theme: ThemeData(
        colorSchemeSeed: Colors.indigo,
        useMaterial3: true,
      ),
      home: const ReportListScreen(),
    );
  }
}
