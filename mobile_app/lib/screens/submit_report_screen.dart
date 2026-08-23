import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';
import 'package:geolocator/geolocator.dart';
import '../services/report_service.dart';

/// Capture a photo + location and submit a new report.
///
/// TODO (team): this currently does NOT actually upload the image anywhere —
/// `imageUrl` is a placeholder. You'll need image upload (e.g. to cloud
/// storage) before submitting the report, since the backend expects a URL,
/// not raw image bytes. Decide on your storage approach as a team.
class SubmitReportScreen extends StatefulWidget {
  const SubmitReportScreen({super.key});

  @override
  State<SubmitReportScreen> createState() => _SubmitReportScreenState();
}

class _SubmitReportScreenState extends State<SubmitReportScreen> {
  final ReportService _service = ReportService();
  XFile? _capturedImage;
  bool _submitting = false;

  Future<void> _capturePhoto() async {
    final picker = ImagePicker();
    final image = await picker.pickImage(source: ImageSource.camera);
    setState(() => _capturedImage = image);
  }

  Future<void> _submit() async {
    if (_capturedImage == null) return;
    setState(() => _submitting = true);
    try {
      final position = await Geolocator.getCurrentPosition();

      // TODO: replace with a real upload step that returns a hosted URL.
      const placeholderImageUrl = 'https://example.com/placeholder.jpg';

      await _service.submitReport(
        imageUrl: placeholderImageUrl,
        latitude: position.latitude,
        longitude: position.longitude,
      );

      if (mounted) Navigator.pop(context);
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context)
            .showSnackBar(SnackBar(content: Text('Failed to submit: $e')));
      }
    } finally {
      if (mounted) setState(() => _submitting = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Report Graffiti')),
      body: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          children: [
            if (_capturedImage != null)
              Text('Photo captured: ${_capturedImage!.name}')
            else
              const Text('No photo captured yet.'),
            const SizedBox(height: 16),
            ElevatedButton.icon(
              onPressed: _capturePhoto,
              icon: const Icon(Icons.camera_alt),
              label: const Text('Take Photo'),
            ),
            const SizedBox(height: 16),
            ElevatedButton(
              onPressed: (_capturedImage != null && !_submitting) ? _submit : null,
              child: _submitting
                  ? const CircularProgressIndicator()
                  : const Text('Submit Report'),
            ),
          ],
        ),
      ),
    );
  }
}
