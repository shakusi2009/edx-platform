"""
Tests to ensure event transformers correctly transform events.
"""
from ddt import (
    ddt,
    data,
    unpack
)

from django.test import TestCase
from xmodule.modulestore.tests.factories import CourseFactory

from lms.djangoapps.django_comment_client.base.event_transformers import (
    ForumThreadViewedEventTransformer,
)
from student.tests.factories import CourseEnrollmentFactory, UserFactory


def _get_processed_event(input_event):
    transformer = ForumThreadViewedEventTransformer(**input_event)
    transformer.process_event()
    return transformer


def _create_event(event_source='mobile', username=None, course_id=None, **event_data):
    result = {'event_source': event_source}
    if course_id:
        if 'context' not in result:
            result['context'] = {}
        result['context']['course_id'] = course_id
    if username:
        result['username'] = username
    if event_data:
        result['event'] = event_data
    return result


class ForumThreadViewedEventTransformerTestCase(TestCase):

    def setUp(self):
        self.course = CourseFactory.create()
        self.student = UserFactory.create()
        CourseEnrollmentFactory.create(user=self.student, course_id=self.course.id)

    def _check_process_event_result(input_event, expected_output_event):
        self.assertDictEqual(_get_processed_event(input_event), expected_output_event)

    def test_empty_event(self):
        self._check_process_event_result({}, {})

    def test_non_mobile_source(self):
        event = {
            'event_source': 'server',
            'event': {
                'course_id': 'course-v1:fake+course+id',
                'discussion_id': 'i4x-edx-fakediscussionid',
                'thread_id': '594d428863623933ee000000'
            }
        }
        self._check_process_event_result(event, event)

    def test_title_truncation(self):
        event = _create_event(title='!')
        self.assertEqual(_get_processed_event(event)['event'].get('title_truncated'), False)
        event = _create_event(title=('covfefe' * 200))
        self.assertTrue(_get_processed_event(event)['event'].get('title_truncated'))

    def test_bad_course_id(self):
        event = _create_event(course_id='not-a-course-id')
        # Just make sure no exception is raised
        _get_processed_event(event)

    def test_bad_username(self):
        event = _create_event(username='not-a-username')
        # Just make sure no exception is raised
        _get_processed_event(event)

    def test_bad_url(self):
        event = _create_event(
            course_id=self.course.id,
            commentable_id='illegal/commentable/id',
            thread_id='illegal/thread/id',
        )
        # Just make sure no exception is raised
        _get_processed_event(event)

    def test_url(self):
        fake_commentable_id = 'fake-commentable-id-1234.'
        fake_thread_id = 'fake-thread-id-1234.'
        event = _create_event(
            course_id=self.course.id,
            commentable_id=fake_commentable_id,
            thread_id=fake_thread_id,
        )
        processed = _get_processed_event(event)
        expected_path = '/courses/{0}/discussion/forum/{1}/threads/{2}'.format(
            self.course.id, fake_commentable_id, fake_thread_id
        )
        self.assertTrue(processed['event'].get('url').endswith(expected_path))

