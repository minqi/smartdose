# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'Prescription'
        db.create_table(u'reminders_prescription', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('patient', self.gf('django.db.models.fields.related.ForeignKey')(related_name='prescriptions_received', to=orm['patients.PatientProfile'])),
            ('prescriber', self.gf('django.db.models.fields.related.ForeignKey')(related_name='prescriptions_given', to=orm['common.UserProfile'])),
            ('safety_net_on', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('last_contacted_safety_net', self.gf('django.db.models.fields.DateTimeField')(null=True)),
            ('drug', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['common.Drug'])),
            ('with_food', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('with_water', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('sig', self.gf('django.db.models.fields.CharField')(max_length=300)),
            ('note', self.gf('django.db.models.fields.CharField')(max_length=300)),
            ('filled', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('last_edited', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, blank=True)),
        ))
        db.send_create_signal(u'reminders', ['Prescription'])

        # Adding model 'Notification'
        db.create_table(u'reminders_notification', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('_type', self.gf('django.db.models.fields.CharField')(max_length=4)),
            ('to', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['patients.PatientProfile'])),
            ('repeat', self.gf('django.db.models.fields.CharField')(max_length=2)),
            ('send_datetime', self.gf('django.db.models.fields.DateTimeField')()),
            ('active', self.gf('django.db.models.fields.BooleanField')(default=True)),
            ('day_of_week', self.gf('django.db.models.fields.PositiveSmallIntegerField')(null=True, blank=True)),
            ('times_sent', self.gf('django.db.models.fields.PositiveIntegerField')(default=0)),
            ('prescription', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['reminders.Prescription'], null=True, blank=True)),
            ('content', self.gf('django.db.models.fields.CharField')(max_length=160, null=True, blank=True)),
            ('patient_of_safety_net', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='patient_of_safety_net', null=True, to=orm['patients.PatientProfile'])),
            ('adherence_rate', self.gf('django.db.models.fields.PositiveSmallIntegerField')(null=True, blank=True)),
            ('message', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='repeat_message', null=True, to=orm['reminders.Message'])),
        ))
        db.send_create_signal(u'reminders', ['Notification'])

        # Adding model 'Message'
        db.create_table(u'reminders_message', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('to', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['patients.PatientProfile'])),
            ('_type', self.gf('django.db.models.fields.CharField')(max_length=4)),
            ('datetime_responded', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
            ('datetime_sent', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('content', self.gf('django.db.models.fields.CharField')(max_length=160)),
            ('previous_message', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['reminders.Message'], null=True, blank=True)),
            ('nth_message_of_day_of_type', self.gf('django.db.models.fields.PositiveSmallIntegerField')(null=True, blank=True)),
        ))
        db.send_create_signal(u'reminders', ['Message'])

        # Adding M2M table for field notifications on 'Message'
        m2m_table_name = db.shorten_name(u'reminders_message_notifications')
        db.create_table(m2m_table_name, (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('message', models.ForeignKey(orm[u'reminders.message'], null=False)),
            ('notification', models.ForeignKey(orm[u'reminders.notification'], null=False))
        ))
        db.create_unique(m2m_table_name, ['message_id', 'notification_id'])

        # Adding M2M table for field feedbacks on 'Message'
        m2m_table_name = db.shorten_name(u'reminders_message_feedbacks')
        db.create_table(m2m_table_name, (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('message', models.ForeignKey(orm[u'reminders.message'], null=False)),
            ('feedback', models.ForeignKey(orm[u'reminders.feedback'], null=False))
        ))
        db.create_unique(m2m_table_name, ['message_id', 'feedback_id'])

        # Adding model 'Feedback'
        db.create_table(u'reminders_feedback', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('_type', self.gf('django.db.models.fields.CharField')(max_length=4)),
            ('notification', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['reminders.Notification'])),
            ('prescription', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['reminders.Prescription'])),
            ('note', self.gf('django.db.models.fields.CharField')(max_length=320)),
            ('completed', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('datetime_sent', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('datetime_responded', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
        ))
        db.send_create_signal(u'reminders', ['Feedback'])


    def backwards(self, orm):
        # Deleting model 'Prescription'
        db.delete_table(u'reminders_prescription')

        # Deleting model 'Notification'
        db.delete_table(u'reminders_notification')

        # Deleting model 'Message'
        db.delete_table(u'reminders_message')

        # Removing M2M table for field notifications on 'Message'
        db.delete_table(db.shorten_name(u'reminders_message_notifications'))

        # Removing M2M table for field feedbacks on 'Message'
        db.delete_table(db.shorten_name(u'reminders_message_feedbacks'))

        # Deleting model 'Feedback'
        db.delete_table(u'reminders_feedback')


    models = {
        u'auth.group': {
            'Meta': {'object_name': 'Group'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        u'auth.permission': {
            'Meta': {'ordering': "(u'content_type__app_label', u'content_type__model', u'codename')", 'unique_together': "((u'content_type', u'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contenttypes.ContentType']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        u'common.drug': {
            'Meta': {'object_name': 'Drug'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '64'})
        },
        u'common.userprofile': {
            'Meta': {'ordering': "['full_name']", 'object_name': 'UserProfile'},
            'address_line1': ('django.db.models.fields.CharField', [], {'max_length': '64'}),
            'address_line2': ('django.db.models.fields.CharField', [], {'max_length': '64'}),
            'auth_token': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'auth_token_active': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'auth_token_datetime': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'auth_token_last_login_datetime': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'auth_token_login_attempts': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'birthday': ('django.db.models.fields.DateField', [], {'null': 'True', 'blank': 'True'}),
            'city': ('django.db.models.fields.CharField', [], {'max_length': '64'}),
            'country_iso_code': ('django.db.models.fields.CharField', [], {'max_length': '2'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '40'}),
            'full_name': ('django.db.models.fields.CharField', [], {'max_length': '80'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "u'user_set'", 'blank': 'True', 'to': u"orm['auth.Group']"}),
            'has_password': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_admin': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'join_datetime': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '40'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'postal_code': ('django.db.models.fields.CharField', [], {'max_length': '10'}),
            'state_province': ('django.db.models.fields.CharField', [], {'max_length': '64'}),
            'status': ('django.db.models.fields.CharField', [], {'default': "'n'", 'max_length': '2'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "u'user_set'", 'blank': 'True', 'to': u"orm['auth.Permission']"}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '40'})
        },
        u'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        u'patients.patientprofile': {
            'Meta': {'ordering': "['full_name']", 'object_name': 'PatientProfile', '_ormbases': [u'common.UserProfile']},
            'age': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'unique': 'True', 'null': 'True', 'blank': 'True'}),
            'enroller': ('django.db.models.fields.related.ForeignKey', [], {'default': 'None', 'related_name': "'enroller'", 'null': 'True', 'blank': 'True', 'to': u"orm['common.UserProfile']"}),
            'gender': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '1'}),
            'height': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'height_unit': ('django.db.models.fields.CharField', [], {'default': "'in'", 'max_length': '2'}),
            'mrn': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'num_caregivers': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'primary_contact': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['patients.PatientProfile']", 'null': 'True'}),
            'primary_phone_number': ('django.db.models.fields.CharField', [], {'max_length': '32', 'unique': 'True', 'null': 'True', 'blank': 'True'}),
            'quit_request_datetime': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'safety_net_contacts': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'safety_net'", 'symmetrical': 'False', 'through': u"orm['patients.SafetyNetRelationship']", 'to': u"orm['patients.PatientProfile']"}),
            u'userprofile_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': u"orm['common.UserProfile']", 'unique': 'True', 'primary_key': 'True'}),
            'weight': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'weight_unit': ('django.db.models.fields.CharField', [], {'default': "'lb'", 'max_length': '2'})
        },
        u'patients.safetynetrelationship': {
            'Meta': {'unique_together': "(('source_patient', 'target_patient'),)", 'object_name': 'SafetyNetRelationship'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'opt_out': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'receives_all_reminders': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'source_patient': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'target_patient_safety_net'", 'to': u"orm['patients.PatientProfile']"}),
            'source_to_target_relationship': ('django.db.models.fields.CharField', [], {'max_length': '20'}),
            'target_patient': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'source_patient_safety_nets'", 'to': u"orm['patients.PatientProfile']"}),
            'target_to_source_relationship': ('django.db.models.fields.CharField', [], {'max_length': '20'})
        },
        u'reminders.feedback': {
            'Meta': {'object_name': 'Feedback'},
            '_type': ('django.db.models.fields.CharField', [], {'max_length': '4'}),
            'completed': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'datetime_responded': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'datetime_sent': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'note': ('django.db.models.fields.CharField', [], {'max_length': '320'}),
            'notification': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['reminders.Notification']"}),
            'prescription': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['reminders.Prescription']"})
        },
        u'reminders.message': {
            'Meta': {'ordering': "['-datetime_sent']", 'object_name': 'Message'},
            '_type': ('django.db.models.fields.CharField', [], {'max_length': '4'}),
            'content': ('django.db.models.fields.CharField', [], {'max_length': '160'}),
            'datetime_responded': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'datetime_sent': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'feedbacks': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'to': u"orm['reminders.Feedback']", 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'notifications': ('django.db.models.fields.related.ManyToManyField', [], {'blank': 'True', 'related_name': "'messages'", 'null': 'True', 'symmetrical': 'False', 'to': u"orm['reminders.Notification']"}),
            'nth_message_of_day_of_type': ('django.db.models.fields.PositiveSmallIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'previous_message': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['reminders.Message']", 'null': 'True', 'blank': 'True'}),
            'to': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['patients.PatientProfile']"})
        },
        u'reminders.notification': {
            'Meta': {'object_name': 'Notification'},
            '_type': ('django.db.models.fields.CharField', [], {'max_length': '4'}),
            'active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'adherence_rate': ('django.db.models.fields.PositiveSmallIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'content': ('django.db.models.fields.CharField', [], {'max_length': '160', 'null': 'True', 'blank': 'True'}),
            'day_of_week': ('django.db.models.fields.PositiveSmallIntegerField', [], {'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'message': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'repeat_message'", 'null': 'True', 'to': u"orm['reminders.Message']"}),
            'patient_of_safety_net': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'patient_of_safety_net'", 'null': 'True', 'to': u"orm['patients.PatientProfile']"}),
            'prescription': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['reminders.Prescription']", 'null': 'True', 'blank': 'True'}),
            'repeat': ('django.db.models.fields.CharField', [], {'max_length': '2'}),
            'send_datetime': ('django.db.models.fields.DateTimeField', [], {}),
            'times_sent': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'to': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['patients.PatientProfile']"})
        },
        u'reminders.prescription': {
            'Meta': {'object_name': 'Prescription'},
            'drug': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['common.Drug']"}),
            'filled': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_contacted_safety_net': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'last_edited': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'note': ('django.db.models.fields.CharField', [], {'max_length': '300'}),
            'patient': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'prescriptions_received'", 'to': u"orm['patients.PatientProfile']"}),
            'prescriber': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'prescriptions_given'", 'to': u"orm['common.UserProfile']"}),
            'safety_net_on': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'sig': ('django.db.models.fields.CharField', [], {'max_length': '300'}),
            'with_food': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'with_water': ('django.db.models.fields.BooleanField', [], {'default': 'False'})
        }
    }

    complete_apps = ['reminders']