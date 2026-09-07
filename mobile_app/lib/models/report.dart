/// Mirrors the backend's ReportOut schema (backend/app/models/schemas.py).
/// Keep these in sync as the API evolves.
class Report {
  final int id;
  final String imageUrl;
  final double latitude;
  final double longitude;
  final String status;
  final String? notes;
  final String? submittedByUuid;
  final String? reporterName;
  final String? reporterEmail;
  final String? reporterPhone;

  Report({
    required this.id,
    required this.imageUrl,
    required this.latitude,
    required this.longitude,
    required this.status,
    this.notes,
    this.submittedByUuid,
    this.reporterName,
    this.reporterEmail,
    this.reporterPhone,
  });

  factory Report.fromJson(
    Map<String, dynamic> json,
  ) {
    return Report(
      id: json['id'],
      imageUrl: json['image_url'],
      latitude: (json['latitude'] as num).toDouble(),
      longitude: (json['longitude'] as num).toDouble(),
      status: json['status'],
      notes: json['notes'],
      submittedByUuid: json['submitted_by_uuid']?.toString(),
      reporterName: json['reporter_name']?.toString(),
      reporterEmail: json['reporter_email']?.toString(),
      reporterPhone: json['reporter_phone']?.toString(),
    );
  }
}
