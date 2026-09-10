import 'package:flutter/material.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

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
    _reportsFuture = _fetchCurrentUserReports();
  }

  Future<List<Report>> _fetchCurrentUserReports() async {
    final currentUser = Supabase.instance.client.auth.currentUser;

    if (currentUser == null) {
      return [];
    }

    final allReports = await _service.fetchReports();

    return allReports
        .where(
          (report) => report.submittedByUuid == currentUser.id,
        )
        .toList();
  }

  void _refresh() {
    setState(() {
      _reportsFuture = _fetchCurrentUserReports();
    });
  }

  Color _statusColour(String status) {
    switch (status.toLowerCase()) {
      case 'resolved':
        return const Color(0xFF22C55E);
      case 'scheduled':
      case 'in progress':
      case 'in_progress':
        return const Color(0xFF38BDF8);
      default:
        return const Color(0xFFFF8A65);
    }
  }

  IconData _statusIcon(String status) {
    switch (status.toLowerCase()) {
      case 'resolved':
        return Icons.check_circle_rounded;
      case 'scheduled':
      case 'in progress':
      case 'in_progress':
        return Icons.schedule_rounded;
      default:
        return Icons.fiber_new_rounded;
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF050505),
      appBar: AppBar(
        backgroundColor: const Color(0xFF050505),
        foregroundColor: Colors.white,
        elevation: 0,
        title: const Text(
          'Your Reports',
          style: TextStyle(fontWeight: FontWeight.w700),
        ),
        actions: [
          IconButton(
            tooltip: 'Refresh',
            onPressed: _refresh,
            icon: const Icon(Icons.refresh_rounded),
          ),
        ],
      ),
      body: Stack(
        children: [
          Positioned(
            top: -120,
            right: -100,
            child: Container(
              width: 260,
              height: 260,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                boxShadow: [
                  BoxShadow(
                    color: const Color(0xFFA855F7).withValues(alpha: 0.16),
                    blurRadius: 100,
                    spreadRadius: 20,
                  ),
                ],
              ),
            ),
          ),
          FutureBuilder<List<Report>>(
            future: _reportsFuture,
            builder: (context, snapshot) {
              if (snapshot.connectionState == ConnectionState.waiting) {
                return const Center(
                  child: CircularProgressIndicator(
                    color: Color(0xFFA855F7),
                  ),
                );
              }

              if (snapshot.hasError) {
                return _ReportMessage(
                  icon: Icons.cloud_off_rounded,
                  title: 'Reports could not be loaded',
                  subtitle: 'Check your connection and try again.',
                  buttonText: 'Try again',
                  onPressed: _refresh,
                );
              }

              final reports = snapshot.data ?? [];
              if (reports.isEmpty) {
                return _ReportMessage(
                  icon: Icons.add_a_photo_rounded,
                  title: 'No reports yet',
                  subtitle:
                      'Your submitted reports and progress will appear here.',
                  buttonText: 'Submit a report',
                  onPressed: () async {
                    await Navigator.push(
                      context,
                      MaterialPageRoute(
                        builder: (_) => const SubmitReportScreen(),
                      ),
                    );
                    _refresh();
                  },
                );
              }

              return RefreshIndicator(
                color: const Color(0xFFA855F7),
                onRefresh: () async => _refresh(),
                child: ListView.separated(
                  physics: const AlwaysScrollableScrollPhysics(),
                  padding: const EdgeInsets.fromLTRB(20, 14, 20, 110),
                  itemCount: reports.length + 1,
                  separatorBuilder: (_, __) => const SizedBox(height: 16),
                  itemBuilder: (context, index) {
                    if (index == 0) {
                      return _ReportSummary(count: reports.length);
                    }

                    final report = reports[index - 1];
                    final statusColour = _statusColour(report.status);

                    return _ReportCard(
                      report: report,
                      statusColour: statusColour,
                      statusIcon: _statusIcon(report.status),
                    );
                  },
                ),
              );
            },
          ),
        ],
      ),
      floatingActionButton: FloatingActionButton(
        onPressed: () async {
          await Navigator.push(
            context,
            MaterialPageRoute(builder: (_) => const SubmitReportScreen()),
          );
          _refresh();
        },
        foregroundColor: Colors.white,
        backgroundColor: const Color(0xFFA855F7),
        child: const Icon(Icons.add_a_photo_rounded),
      ),
    );
  }
}

class _ReportSummary extends StatelessWidget {
  final int count;

  const _ReportSummary({required this.count});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        gradient: const LinearGradient(
          colors: [Color(0xFFFF5F8F), Color(0xFFA855F7), Color(0xFF3B82F6)],
        ),
        borderRadius: BorderRadius.circular(24),
        boxShadow: [
          BoxShadow(
            color: const Color(0xFFA855F7).withValues(alpha: 0.25),
            blurRadius: 24,
            offset: const Offset(0, 10),
          ),
        ],
      ),
      child: Row(
        children: [
          Container(
            width: 52,
            height: 52,
            decoration: BoxDecoration(
              color: Colors.white.withValues(alpha: 0.18),
              borderRadius: BorderRadius.circular(17),
            ),
            child: const Icon(Icons.receipt_long_rounded, color: Colors.white),
          ),
          const SizedBox(width: 16),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  '$count submitted ${count == 1 ? 'report' : 'reports'}',
                  style: const TextStyle(
                    color: Colors.white,
                    fontSize: 19,
                    fontWeight: FontWeight.w700,
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  'Follow the progress of reports you created.',
                  style: TextStyle(
                    color: Colors.white.withValues(alpha: 0.78),
                    fontSize: 12,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _ReportCard extends StatelessWidget {
  final Report report;
  final Color statusColour;
  final IconData statusIcon;

  const _ReportCard({
    required this.report,
    required this.statusColour,
    required this.statusIcon,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      clipBehavior: Clip.antiAlias,
      decoration: BoxDecoration(
        gradient: LinearGradient(
          colors: [
            statusColour.withValues(alpha: 0.38),
            const Color(0xFF151515),
          ],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
        borderRadius: BorderRadius.circular(23),
        border: Border.all(color: statusColour.withValues(alpha: 0.55)),
        boxShadow: [
          BoxShadow(
            color: statusColour.withValues(alpha: 0.13),
            blurRadius: 18,
            offset: const Offset(0, 8),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            height: 155,
            width: double.infinity,
            child: Image.network(
              report.imageUrl,
              fit: BoxFit.cover,
              errorBuilder: (_, __, ___) => ColoredBox(
                color: const Color(0xFF202020),
                child: Icon(
                  Icons.image_not_supported_rounded,
                  color: Colors.white.withValues(alpha: 0.45),
                  size: 38,
                ),
              ),
            ),
          ),
          Padding(
            padding: const EdgeInsets.all(17),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Expanded(
                      child: Text(
                        'Report #${report.id}',
                        style: const TextStyle(
                          color: Colors.white,
                          fontSize: 18,
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                    ),
                    Container(
                      padding: const EdgeInsets.symmetric(
                        horizontal: 11,
                        vertical: 7,
                      ),
                      decoration: BoxDecoration(
                        color: statusColour.withValues(alpha: 0.20),
                        borderRadius: BorderRadius.circular(20),
                        border: Border.all(
                          color: statusColour.withValues(alpha: 0.65),
                        ),
                      ),
                      child: Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Icon(statusIcon, color: statusColour, size: 16),
                          const SizedBox(width: 6),
                          Text(
                            report.status,
                            style: TextStyle(
                              color: statusColour,
                              fontSize: 11,
                              fontWeight: FontWeight.w700,
                            ),
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
                if (report.notes != null &&
                    report.notes!.trim().isNotEmpty) ...[
                  const SizedBox(height: 10),
                  Text(
                    report.notes!,
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(
                      color: Colors.white70,
                      fontSize: 13,
                      height: 1.4,
                    ),
                  ),
                ],
                const SizedBox(height: 13),
                Row(
                  children: [
                    const Icon(
                      Icons.location_on_rounded,
                      color: Color(0xFF38BDF8),
                      size: 18,
                    ),
                    const SizedBox(width: 7),
                    Expanded(
                      child: Text(
                        '${report.latitude.toStringAsFixed(5)}, ${report.longitude.toStringAsFixed(5)}',
                        style: const TextStyle(
                          color: Colors.white60,
                          fontSize: 12,
                        ),
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _ReportMessage extends StatelessWidget {
  final IconData icon;
  final String title;
  final String subtitle;
  final String buttonText;
  final VoidCallback onPressed;

  const _ReportMessage({
    required this.icon,
    required this.title,
    required this.subtitle,
    required this.buttonText,
    required this.onPressed,
  });

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(30),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Container(
              width: 78,
              height: 78,
              decoration: BoxDecoration(
                gradient: const LinearGradient(
                  colors: [Color(0xFFA855F7), Color(0xFF3B82F6)],
                ),
                borderRadius: BorderRadius.circular(25),
              ),
              child: Icon(icon, color: Colors.white, size: 36),
            ),
            const SizedBox(height: 22),
            Text(
              title,
              textAlign: TextAlign.center,
              style: const TextStyle(
                color: Colors.white,
                fontSize: 21,
                fontWeight: FontWeight.w700,
              ),
            ),
            const SizedBox(height: 8),
            Text(
              subtitle,
              textAlign: TextAlign.center,
              style: const TextStyle(color: Colors.white60, height: 1.4),
            ),
            const SizedBox(height: 22),
            FilledButton.icon(
              onPressed: onPressed,
              icon: const Icon(Icons.arrow_forward_rounded),
              label: Text(buttonText),
              style: FilledButton.styleFrom(
                backgroundColor: const Color(0xFFA855F7),
                foregroundColor: Colors.white,
                padding: const EdgeInsets.symmetric(
                  horizontal: 20,
                  vertical: 14,
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
