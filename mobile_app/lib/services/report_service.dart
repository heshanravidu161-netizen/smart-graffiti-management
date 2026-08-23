import 'dart:convert';
import 'package:http/http.dart' as http;
import '../models/report.dart';

/// Talks to the backend skeleton (backend/app/routers/reports.py).
///
/// TODO (team): move the base URL into a config/env file before you have
/// multiple people running this against different backends (local vs
/// deployed). Also add proper error handling — this is bare-bones.
class ReportService {
  static const String baseUrl = 'http://localhost:8000';

  Future<List<Report>> fetchReports({String? status}) async {
    final uri = status != null
        ? Uri.parse('$baseUrl/reports/?status=$status')
        : Uri.parse('$baseUrl/reports/');
    final response = await http.get(uri);
    if (response.statusCode != 200) {
      throw Exception('Failed to load reports (${response.statusCode})');
    }
    final List<dynamic> data = jsonDecode(response.body);
    return data.map((json) => Report.fromJson(json)).toList();
  }

  Future<Report> submitReport({
    required String imageUrl,
    required double latitude,
    required double longitude,
    String? notes,
  }) async {
    final response = await http.post(
      Uri.parse('$baseUrl/reports/'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({
        'image_url': imageUrl,
        'latitude': latitude,
        'longitude': longitude,
        'notes': notes,
      }),
    );
    if (response.statusCode != 200) {
      throw Exception('Failed to submit report (${response.statusCode})');
    }
    return Report.fromJson(jsonDecode(response.body));
  }
}
