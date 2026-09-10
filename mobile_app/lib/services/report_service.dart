import 'dart:convert';

import 'package:http/http.dart' as http;

import '../models/report.dart';

class ReportService {
  static const String baseUrl = 'https://urbaneyes-backend.onrender.com';

  Future<List<Report>> fetchReports({
    String? status,
  }) async {
    final uri = status != null
        ? Uri.parse(
            '$baseUrl/reports/?status=$status',
          )
        : Uri.parse('$baseUrl/reports/');

    final response = await http.get(uri);

    if (response.statusCode != 200) {
      throw Exception(
        'Failed to load reports '
        '(${response.statusCode}): ${response.body}',
      );
    }

    final List<dynamic> data = jsonDecode(response.body);

    return data
        .map(
          (item) => Report.fromJson(item),
        )
        .toList();
  }

  Future<Report> submitReport({
    required String imageUrl,
    required double latitude,
    required double longitude,
    required String submittedByUuid,
    required String reporterEmail,
    String? reporterName,
    String? reporterPhone,
    String? notes,
  }) async {
    final requestData = {
      'image_url': imageUrl,
      'latitude': latitude,
      'longitude': longitude,
      'notes': notes,
      'submitted_by_uuid': submittedByUuid,
      'reporter_name': reporterName,
      'reporter_email': reporterEmail,
      'reporter_phone': reporterPhone,
    };

    final response = await http.post(
      Uri.parse('$baseUrl/reports/'),
      headers: {
        'Content-Type': 'application/json',
      },
      body: jsonEncode(requestData),
    );

    if (response.statusCode != 200) {
      throw Exception(
        'Failed to submit report '
        '(${response.statusCode}): ${response.body}',
      );
    }

    return Report.fromJson(
      jsonDecode(response.body),
    );
  }
}
