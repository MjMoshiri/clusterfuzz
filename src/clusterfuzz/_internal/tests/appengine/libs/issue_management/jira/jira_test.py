# Copyright 2020 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Tests for jira issue management."""

import datetime
import unittest

import pytz

from clusterfuzz._internal.tests.test_libs import helpers
from libs.issue_management import jira
from libs.issue_management.jira import Issue
from libs.issue_management.jira import issue_tracker_manager


class Config(object):
  """Dummy config."""

  def __init__(self):
    self.jira_url = 'https://jira.company.com'


class Reporter(object):
  """Dummy reporter."""

  def __init__(self):
    self.display_name = 'Reporter'
    self.key = 'reporter'
    self.name = 'reporter'


class Status(object):
  """Dummy status."""

  def __init__(self):
    self.name = 'NOT STARTED'


class Fields(object):
  """Dummy fields."""

  def __init__(self):
    self.assignee = 'Unassigned'
    self.summary = 'summary'
    self.description = 'body'
    self.reporter = Reporter()
    self.status = Status()
    self.labels = []
    self.components = []
    self.resolutiondate = '2020-01-14T11:46:34.000-0000'


class JiraIssue(object):
  """Dummy Jira issue."""

  def __init__(self, key):
    self.key = key
    self.id = key.split('-')[-1]
    self.fields = Fields()

  def update(self, **kwargs):
    pass


class JiraTests(unittest.TestCase):
  """Tests for the jira issue tracker."""

  def setUp(self):
    helpers.patch(self, [
        'libs.issue_management.jira.issue_tracker_manager.'
        'IssueTrackerManager.get_watchers',
        'libs.issue_management.jira.issue_tracker_manager.'
        'IssueTrackerManager.get_issues',
        'libs.issue_management.jira.IssueTracker.get_issue',
        'libs.issue_management.jira.IssueTracker.new_issue',
        'clusterfuzz._internal.config.db_config.get',
        'libs.issue_management.jira.issue_tracker_manager.'
        'IssueTrackerManager.client'
    ])

    self.itm = issue_tracker_manager.IssueTrackerManager('VSEC')
    self.issue_tracker = jira.IssueTracker(self.itm)
    self.jira_issue = JiraIssue('VSEC-3112')
    self.mock.get_watchers.return_value = []

    self.mock_issue = Issue(self.itm, self.jira_issue)
    self.mock_issue.title = 'summary'
    self.mock_issue.body = 'body'
    self.mock_issue.reporter = 'reporter'
    self.mock_issue.status = 'NOT STARTED'
    self.mock_issue.labels.add('label1')
    self.mock_issue.labels.add('label2')
    self.mock_issue.components.add('A>B')
    self.mock_issue.components.add('C>D')
    self.mock_issue.ccs.add('cc@cc.com')

  def test_get_issue(self):
    """Test get_issue."""
    self.mock.get_issue.return_value = self.mock_issue
    issue = self.issue_tracker.get_issue('VSEC-3112')

    self.assertEqual(3112, issue.id)
    self.assertEqual('VSEC-3112', issue.key)
    self.assertEqual('summary', issue.title)
    self.assertEqual('body', issue.body)
    self.assertEqual('Unassigned', issue.assignee)
    self.assertEqual('reporter', issue.reporter)
    self.assertEqual('NOT STARTED', issue.status)

    self.assertCountEqual([
        'label1',
        'label2',
    ], issue.labels)
    self.assertCountEqual([
        'A>B',
        'C>D',
    ], issue.components)
    self.assertCountEqual([
        'cc@cc.com',
    ], issue.ccs)

    issue = self.issue_tracker.get_issue('VSEC-3112')
    self.assertEqual('VSEC-3112', issue.key)
    self.assertEqual(
        datetime.datetime(2020, 1, 14, 11, 46, 34, tzinfo=pytz.utc).timestamp(),
        issue.closed_time.timestamp())

  def test_modify_labels(self):
    """Test modifying labels."""
    self.mock.get_issue.return_value = self.mock_issue
    issue = self.issue_tracker.get_issue('VSEC-3112')
    issue.labels.add('Label3')
    issue.labels.remove('laBel1')
    self.assertCountEqual(['label2', 'Label3'], issue.labels)

  def test_modify_components(self):
    """Test modifying components."""
    self.mock.get_issue.return_value = self.mock_issue
    issue = self.issue_tracker.get_issue('VSEC-3112')
    issue.components.add('Y>Z')
    issue.components.remove('a>B')
    self.assertCountEqual(['C>D', 'Y>Z'], issue.components)

  def test_find_issues(self):
    """Test find_issues."""
    self.mock.get_issues.return_value = [self.jira_issue]
    issues = self.issue_tracker.find_issues(keywords=['body'], only_open=True)
    self.assertCountEqual(['VSEC-3112'], [issue.key for issue in issues])

  def test_issue_url(self):
    """Test issue_url."""
    self.mock.get.return_value = Config()
    self.mock.get_issue.return_value = self.mock_issue
    issue_url = self.issue_tracker.issue_url('VSEC-3112')
    self.assertEqual('https://jira.company.com/browse/VSEC-3112', issue_url)

  def test_find_issues_url(self):
    """Test find_issues_url."""
    self.mock.get.return_value = Config()
    issue_url = self.issue_tracker.find_issues_url(
        keywords=['keyword+-&|!(){}[]^~*?:+-&|!(){}[]^~*?:test'])
    self.assertEqual(
        'https://jira.company.com/issues/?jql=project = VSEC AND text ~ "keyword test"',
        issue_url)

  def test_issue_save(self):
    """Test save."""
    self.mock.get_issue.return_value = self.mock_issue
    issue = self.issue_tracker.get_issue('VSEC-3112')
    issue.status = 'Closed'
    issue.save(new_comment='test comments')
    self.mock.client.add_comment.assert_called_with(self.mock_issue.jira_issue,
                                                    'test comments')
    self.assertEqual(issue.status, 'Closed')
