/// Mirrors the backend's ReportOut schema (backend/app/models/schemas.py).
/// Keep these in sync as the API evolves.
class Report {
  final int id;
  final String imageUrl;
  final double latitude;
  final double longitude;
  final String status;
  final String? notes;

  Report({
    required this.id,
    required this.imageUrl,
    required this.latitude,
    required this.longitude,
    required this.status,
    this.notes,
  });

  factory Report.fromJson(Map<String, dynamic> json) {
    return Report(
      id: json['id'],
      imageUrl: json['image_url'],
      latitude: (json['latitude'] as num).toDouble(),
      longitude: (json['longitude'] as num).toDouble(),
      status: json['status'],
      notes: json['notes'],
    );
  }
}
