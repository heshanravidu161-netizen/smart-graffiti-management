import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:latlong2/latlong.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

import '../models/report.dart';
import '../services/report_service.dart';
import 'report_list_screen.dart';
import 'submit_report_screen.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  final ReportService _reportService = ReportService();
  late Future<List<Report>> _myReportsFuture;
  late Future<List<Report>> _communityReportsFuture;

  @override
  void initState() {
    super.initState();
    _setReportFutures();
  }

  void _setReportFutures() {
    final userId = Supabase.instance.client.auth.currentUser?.id;
    final allReportsFuture = _reportService.fetchReports();

    _communityReportsFuture = allReportsFuture;
    _myReportsFuture = allReportsFuture.then((reports) {
      if (userId == null) return <Report>[];

      return reports
          .where((report) => report.submittedByUuid == userId)
          .toList();
    });
  }

  void _refreshReports() {
    setState(() {
      _setReportFutures();
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF050505),
      body: Stack(
        children: [
          const Positioned(
              top: -130,
              right: -110,
              child: _GlowOrb(size: 300, colour: Color(0xFFA855F7))),
          const Positioned(
              bottom: -170,
              left: -130,
              child: _GlowOrb(size: 330, colour: Color(0xFF22B8F5))),
          SafeArea(
            child: SingleChildScrollView(
              padding: const EdgeInsets.fromLTRB(22, 18, 22, 34),
              child: Center(
                child: ConstrainedBox(
                  constraints: const BoxConstraints(maxWidth: 500),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const _Header(),
                      const SizedBox(height: 34),
                      const Text(
                        '🇦🇺 Keep Australia Beautiful',
                        style: TextStyle(
                            color: Colors.white,
                            fontSize: 32,
                            height: 1.12,
                            letterSpacing: -0.5,
                            fontWeight: FontWeight.w700),
                      ),
                      const SizedBox(height: 14),
                      Text(
                        'Help councils respond faster by sharing clear, accurate graffiti reports from your community ❤️',
                        style: TextStyle(
                            color: Colors.white.withValues(alpha: 0.58),
                            fontSize: 15,
                            height: 1.45),
                      ),
                      const SizedBox(height: 26),
                      _PrimaryAction(
                        onTap: () => Navigator.push(
                          context,
                          MaterialPageRoute(
                              builder: (_) => const SubmitReportScreen()),
                        ),
                      ),
                      const SizedBox(height: 18),
                      const Row(
                        children: [
                          Expanded(
                              child: _MiniStat(
                                  value: '3 steps',
                                  label: 'Quick reporting',
                                  icon: Icons.bolt_rounded,
                                  colour: Color(0xFFFF8A65))),
                          SizedBox(width: 12),
                          Expanded(
                              child: _MiniStat(
                                  value: 'Live',
                                  label: 'Status tracking',
                                  icon: Icons.track_changes_rounded,
                                  colour: Color(0xFF38BDF8))),
                        ],
                      ),
                      const SizedBox(height: 18),
                      _SecondaryAction(
                        icon: Icons.receipt_long_rounded,
                        title: 'Your reports',
                        subtitle: 'Follow progress and council updates',
                        onTap: () => Navigator.push(
                          context,
                          MaterialPageRoute(builder: (_) => ReportListScreen()),
                        ),
                      ),
                      const SizedBox(height: 24),
                      _ReportsMapCard(
                        title: 'Your reports map',
                        subtitle: 'Tap a marker to view your report progress',
                        emptyTitle: 'No submitted reports yet',
                        emptySubtitle:
                            'Your report locations will appear here.',
                        footer:
                            'Your report progress is read-only. Only authorised council staff can change a status.',
                        reportsFuture: _myReportsFuture,
                        onRefresh: _refreshReports,
                      ),
                      const SizedBox(height: 24),
                      const _CommunityCard(),
                      const SizedBox(height: 24),
                      _ReportsMapCard(
                        title: 'Community reports map',
                        subtitle: 'Tap a marker to view its progress',
                        emptyTitle: 'No community reports yet',
                        emptySubtitle:
                            'Community report locations will appear here.',
                        footer:
                            'Reporter identities are hidden. Progress is read-only and can only be changed by authorised council staff.',
                        reportsFuture: _communityReportsFuture,
                        onRefresh: _refreshReports,
                      ),
                    ],
                  ),
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _ReportsMapCard extends StatelessWidget {
  final String title;
  final String subtitle;
  final String emptyTitle;
  final String emptySubtitle;
  final String footer;
  final Future<List<Report>> reportsFuture;
  final VoidCallback onRefresh;

  const _ReportsMapCard({
    required this.title,
    required this.subtitle,
    required this.emptyTitle,
    required this.emptySubtitle,
    required this.footer,
    required this.reportsFuture,
    required this.onRefresh,
  });

  Color _markerColour(String status) {
    switch (status.toLowerCase()) {
      case 'resolved':
        return const Color(0xFF4CAF50);
      case 'scheduled':
      case 'in progress':
      case 'in_progress':
        return const Color(0xFF2196F3);
      default:
        return const Color(0xFFFF9800);
    }
  }

  void _showReportProgress(BuildContext context, Report report) {
    ScaffoldMessenger.of(context).hideCurrentSnackBar();
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text('Report #${report.id} • Progress: ${report.status}'),
        backgroundColor: _markerColour(report.status),
        behavior: SnackBarBehavior.floating,
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        gradient: const LinearGradient(
          colors: [Color(0xFF172554), Color(0xFF312E81)],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
        borderRadius: BorderRadius.circular(24),
        border:
            Border.all(color: const Color(0xFF60A5FA).withValues(alpha: 0.45)),
        boxShadow: [
          BoxShadow(
            color: const Color(0xFF2563EB).withValues(alpha: 0.18),
            blurRadius: 24,
            offset: const Offset(0, 10),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      title,
                      style: const TextStyle(
                        color: Colors.white,
                        fontSize: 18,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                    SizedBox(height: 4),
                    Text(
                      subtitle,
                      style: const TextStyle(
                        color: Colors.white70,
                        fontSize: 12,
                      ),
                    ),
                  ],
                ),
              ),
              IconButton(
                tooltip: 'Refresh reports',
                onPressed: onRefresh,
                icon: const Icon(Icons.refresh_rounded, color: Colors.white),
              ),
            ],
          ),
          const SizedBox(height: 14),
          ClipRRect(
            borderRadius: BorderRadius.circular(18),
            child: SizedBox(
              height: 285,
              child: FutureBuilder<List<Report>>(
                future: reportsFuture,
                builder: (context, snapshot) {
                  if (snapshot.connectionState == ConnectionState.waiting) {
                    return const ColoredBox(
                      color: Color(0xFF111827),
                      child: Center(
                        child:
                            CircularProgressIndicator(color: Color(0xFF60A5FA)),
                      ),
                    );
                  }

                  if (snapshot.hasError) {
                    return _MapMessage(
                      icon: Icons.cloud_off_rounded,
                      title: 'Reports could not be loaded',
                      subtitle: 'Check your connection and tap refresh.',
                      onRetry: onRefresh,
                    );
                  }

                  final reports = snapshot.data ?? [];
                  if (reports.isEmpty) {
                    return _MapMessage(
                      icon: Icons.location_off_rounded,
                      title: emptyTitle,
                      subtitle: emptySubtitle,
                    );
                  }

                  final firstReport = reports.first;

                  return FlutterMap(
                    options: MapOptions(
                      initialCenter: LatLng(
                        firstReport.latitude,
                        firstReport.longitude,
                      ),
                      initialZoom: 12,
                    ),
                    children: [
                      TileLayer(
                        urlTemplate:
                            'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
                        userAgentPackageName: 'com.urbaneyes.mobile_app',
                      ),
                      MarkerLayer(
                        markers: reports.map((report) {
                          final colour = _markerColour(report.status);

                          return Marker(
                            point: LatLng(
                              report.latitude,
                              report.longitude,
                            ),
                            width: 46,
                            height: 46,
                            child: GestureDetector(
                              onTap: () => _showReportProgress(context, report),
                              child: Stack(
                                alignment: Alignment.center,
                                children: [
                                  Icon(
                                    Icons.location_on_rounded,
                                    color: colour,
                                    size: 44,
                                    shadows: const [
                                      Shadow(
                                        color: Colors.black87,
                                        blurRadius: 8,
                                      ),
                                    ],
                                  ),
                                  const Positioned(
                                    top: 8,
                                    child: Icon(
                                      Icons.circle,
                                      color: Colors.white,
                                      size: 9,
                                    ),
                                  ),
                                ],
                              ),
                            ),
                          );
                        }).toList(),
                      ),
                      const RichAttributionWidget(
                        attributions: [
                          TextSourceAttribution('Esri'),
                        ],
                      ),
                    ],
                  );
                },
              ),
            ),
          ),
          const SizedBox(height: 14),
          const Wrap(
            spacing: 14,
            runSpacing: 8,
            children: [
              _MapLegend(colour: Color(0xFFFF9800), label: 'New'),
              _MapLegend(colour: Color(0xFF2196F3), label: 'Scheduled'),
              _MapLegend(colour: Color(0xFF4CAF50), label: 'Resolved'),
            ],
          ),
          const SizedBox(height: 10),
          Text(
            footer,
            style: const TextStyle(
              color: Colors.white60,
              fontSize: 11,
              height: 1.35,
            ),
          ),
        ],
      ),
    );
  }
}

class _MapMessage extends StatelessWidget {
  final IconData icon;
  final String title;
  final String subtitle;
  final VoidCallback? onRetry;

  const _MapMessage({
    required this.icon,
    required this.title,
    required this.subtitle,
    this.onRetry,
  });

  @override
  Widget build(BuildContext context) {
    return ColoredBox(
      color: const Color(0xFF111827),
      child: Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(icon, color: const Color(0xFF60A5FA), size: 36),
              const SizedBox(height: 10),
              Text(
                title,
                textAlign: TextAlign.center,
                style: const TextStyle(
                  color: Colors.white,
                  fontSize: 15,
                  fontWeight: FontWeight.w700,
                ),
              ),
              const SizedBox(height: 5),
              Text(
                subtitle,
                textAlign: TextAlign.center,
                style: const TextStyle(color: Colors.white60, fontSize: 12),
              ),
              if (onRetry != null) ...[
                const SizedBox(height: 12),
                TextButton(
                  onPressed: onRetry,
                  child: const Text('Try again'),
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }
}

class _MapLegend extends StatelessWidget {
  final Color colour;
  final String label;

  const _MapLegend({required this.colour, required this.label});

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Container(
          width: 9,
          height: 9,
          decoration: BoxDecoration(color: colour, shape: BoxShape.circle),
        ),
        const SizedBox(width: 6),
        Text(label,
            style: const TextStyle(color: Colors.white70, fontSize: 11)),
      ],
    );
  }
}

class _Header extends StatelessWidget {
  const _Header();

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Container(
          width: 40,
          height: 40,
          decoration: BoxDecoration(
            gradient: const LinearGradient(colors: [
              Color(0xFFFF8FCB),
              Color(0xFF8B5CF6),
              Color(0xFF22B8F5)
            ]),
            borderRadius: BorderRadius.circular(13),
          ),
          child: const Icon(Icons.remove_red_eye_rounded,
              color: Colors.white, size: 23),
        ),
        const SizedBox(width: 11),
        const Text('UrbanEyes',
            style: TextStyle(
                color: Colors.white,
                fontSize: 21,
                fontWeight: FontWeight.w800,
                letterSpacing: -0.4)),
        const Spacer(),
        PopupMenuButton<String>(
          color: const Color(0xFF181818),
          offset: const Offset(0, 50),
          shape:
              RoundedRectangleBorder(borderRadius: BorderRadius.circular(18)),
          onSelected: (value) {
            if (value == 'report') {
              Navigator.push(
                  context,
                  MaterialPageRoute(
                      builder: (_) => const SubmitReportScreen()));
            } else if (value == 'history') {
              Navigator.push(context,
                  MaterialPageRoute(builder: (_) => ReportListScreen()));
            }
          },
          itemBuilder: (context) => const [
            PopupMenuItem(
              value: 'report',
              child: Row(children: [
                Icon(Icons.add_a_photo_rounded, color: Color(0xFFA855F7)),
                SizedBox(width: 12),
                Text('Submit report', style: TextStyle(color: Colors.white)),
              ]),
            ),
            PopupMenuItem(
              value: 'history',
              child: Row(children: [
                Icon(Icons.receipt_long_rounded, color: Color(0xFF38BDF8)),
                SizedBox(width: 12),
                Text('Your reports', style: TextStyle(color: Colors.white)),
              ]),
            ),
          ],
          child: Container(
            width: 42,
            height: 42,
            decoration: BoxDecoration(
                color: const Color(0xFF171717),
                borderRadius: BorderRadius.circular(15),
                border: Border.all(color: Colors.white12)),
            child:
                const Icon(Icons.menu_rounded, color: Colors.white, size: 22),
          ),
        ),
      ],
    );
  }
}

class _PrimaryAction extends StatelessWidget {
  final VoidCallback onTap;
  const _PrimaryAction({required this.onTap});

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(28),
        gradient: const LinearGradient(
            colors: [Color(0xFFFF5F8F), Color(0xFFA855F7), Color(0xFF3B82F6)],
            begin: Alignment.topLeft,
            end: Alignment.bottomRight),
        boxShadow: [
          BoxShadow(
              color: const Color(0xFFA855F7).withValues(alpha: 0.28),
              blurRadius: 28,
              offset: const Offset(0, 14))
        ],
      ),
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          borderRadius: BorderRadius.circular(28),
          onTap: onTap,
          child: Padding(
            padding: const EdgeInsets.all(22),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Container(
                      width: 48,
                      height: 48,
                      decoration: BoxDecoration(
                          color: Colors.white.withValues(alpha: 0.18),
                          borderRadius: BorderRadius.circular(16)),
                      child: const Icon(Icons.add_a_photo_rounded,
                          color: Colors.white),
                    ),
                    const Spacer(),
                    Container(
                      width: 44,
                      height: 44,
                      decoration: const BoxDecoration(
                          color: Colors.white, shape: BoxShape.circle),
                      child: const Icon(Icons.arrow_forward_rounded,
                          color: Color(0xFF6C20E8)),
                    ),
                  ],
                ),
                const SizedBox(height: 34),
                const Text('Report graffiti',
                    style: TextStyle(
                        color: Colors.white,
                        fontSize: 24,
                        fontWeight: FontWeight.w700)),
                const SizedBox(height: 7),
                Text(
                  'Take a photo, confirm the location and send it to council.',
                  style: TextStyle(
                      color: Colors.white.withValues(alpha: 0.78),
                      fontSize: 14,
                      height: 1.4),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _MiniStat extends StatelessWidget {
  final String value;
  final String label;
  final IconData icon;
  final Color colour;
  const _MiniStat(
      {required this.value,
      required this.label,
      required this.icon,
      required this.colour});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        gradient: LinearGradient(
          colors: [
            colour.withValues(alpha: 0.62),
            colour.withValues(alpha: 0.25),
          ],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: colour.withValues(alpha: 0.72)),
        boxShadow: [
          BoxShadow(
            color: colour.withValues(alpha: 0.16),
            blurRadius: 18,
            offset: const Offset(0, 8),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            width: 34,
            height: 34,
            decoration: BoxDecoration(
                color: Colors.white.withValues(alpha: 0.18),
                borderRadius: BorderRadius.circular(11)),
            child: Icon(icon, color: Colors.white, size: 19),
          ),
          const SizedBox(height: 14),
          Text(value,
              style: const TextStyle(
                  color: Colors.white,
                  fontSize: 17,
                  fontWeight: FontWeight.w700)),
          const SizedBox(height: 3),
          Text(label,
              style: TextStyle(
                  color: Colors.white.withValues(alpha: 0.76), fontSize: 11)),
        ],
      ),
    );
  }
}

class _SecondaryAction extends StatelessWidget {
  final IconData icon;
  final String title;
  final String subtitle;
  final VoidCallback onTap;
  const _SecondaryAction(
      {required this.icon,
      required this.title,
      required this.subtitle,
      required this.onTap});

  @override
  Widget build(BuildContext context) {
    return Material(
      color: Colors.transparent,
      borderRadius: BorderRadius.circular(22),
      child: InkWell(
        borderRadius: BorderRadius.circular(22),
        onTap: onTap,
        child: Container(
          padding: const EdgeInsets.all(18),
          decoration: BoxDecoration(
            gradient: const LinearGradient(
              colors: [Color(0xFF2563EB), Color(0xFF06B6D4)],
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
            ),
            borderRadius: BorderRadius.circular(22),
            boxShadow: [
              BoxShadow(
                color: const Color(0xFF0EA5E9).withValues(alpha: 0.20),
                blurRadius: 20,
                offset: const Offset(0, 9),
              ),
            ],
          ),
          child: Row(
            children: [
              Container(
                width: 48,
                height: 48,
                decoration: BoxDecoration(
                    color: Colors.white.withValues(alpha: 0.18),
                    borderRadius: BorderRadius.circular(16)),
                child: Icon(icon, color: Colors.white),
              ),
              const SizedBox(width: 15),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(title,
                        style: const TextStyle(
                            color: Colors.white,
                            fontSize: 17,
                            fontWeight: FontWeight.w700)),
                    const SizedBox(height: 4),
                    Text(subtitle,
                        style: TextStyle(
                            color: Colors.white.withValues(alpha: 0.78),
                            fontSize: 12)),
                  ],
                ),
              ),
              const Icon(Icons.chevron_right_rounded, color: Colors.white),
            ],
          ),
        ),
      ),
    );
  }
}

class _CommunityCard extends StatelessWidget {
  const _CommunityCard();

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        gradient: const LinearGradient(
          colors: [Color(0xFF7C3AED), Color(0xFFDB2777)],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
        borderRadius: BorderRadius.circular(24),
        border: Border.all(color: Colors.white24),
        boxShadow: [
          BoxShadow(
            color: const Color(0xFFDB2777).withValues(alpha: 0.18),
            blurRadius: 20,
            offset: const Offset(0, 9),
          ),
        ],
      ),
      child: Row(
        children: [
          const Icon(Icons.public_rounded, color: Colors.white, size: 32),
          const SizedBox(width: 15),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text('Better streets start with you',
                    style: TextStyle(
                        color: Colors.white,
                        fontSize: 15,
                        fontWeight: FontWeight.w700)),
                const SizedBox(height: 4),
                Text(
                  'Every accurate report helps build a cleaner community.',
                  style: TextStyle(
                      color: Colors.white.withValues(alpha: 0.78),
                      fontSize: 12,
                      height: 1.35),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _GlowOrb extends StatelessWidget {
  final double size;
  final Color colour;
  const _GlowOrb({required this.size, required this.colour});

  @override
  Widget build(BuildContext context) {
    return IgnorePointer(
      child: Container(
        width: size,
        height: size,
        decoration: BoxDecoration(
          shape: BoxShape.circle,
          boxShadow: [
            BoxShadow(
                color: colour.withValues(alpha: 0.13),
                blurRadius: 100,
                spreadRadius: 25)
          ],
        ),
      ),
    );
  }
}
