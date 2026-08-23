import 'package:flutter/material.dart';
import '../models/report.dart';
import '../services/report_service.dart';
import 'submit_report_screen.dart';

/// Lists submitted reports. In the real app this is where the map view and
/// filtering (by status/severity) will live — currently just a plain list.
class ReportListScreen extends StatefulWidget {
  const ReportListScreen({super.key});

  @override
  State<ReportListScreen> createState() => _ReportListScreenState();
}

class _ReportListScreenState extends State<ReportListScreen> {
  final ReportService _service = ReportService();
  late Future<List<Report>> _reportsFuture;

  @override
  void initState() {
    super.initState();
    _reportsFuture = _service.fetchReports();
  }

  void _refresh() {
    setState(() {
      _reportsFuture = _service.fetchReports();
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Graffiti Reports')),
      body: FutureBuilder<List<Report>>(
        future: _reportsFuture,
        builder: (context, snapshot) {
          if (snapshot.connectionState == ConnectionState.waiting) {
            return const Center(child: CircularProgressIndicator());
          }
          if (snapshot.hasError) {
            // TODO: friendlier error state, retry button, offline handling
            return Center(child: Text('Error: ${snapshot.error}'));
          }
          final reports = snapshot.data ?? [];
          if (reports.isEmpty) {
            return const Center(child: Text('No reports yet.'));
          }
          return ListView.builder(
            itemCount: reports.length,
            itemBuilder: (context, index) {
              final r = reports[index];
              return ListTile(
                title: Text('Report #${r.id} — ${r.status}'),
                subtitle: Text('(${r.latitude}, ${r.longitude})'),
                // TODO: navigate to a detail screen showing the AI classification
              );
            },
          );
        },
      ),
      floatingActionButton: FloatingActionButton(
        onPressed: () async {
          await Navigator.push(
            context,
            MaterialPageRoute(builder: (_) => const SubmitReportScreen()),
          );
          _refresh();
        },
        child: const Icon(Icons.add_a_photo),
      ),
    );
  }
}
