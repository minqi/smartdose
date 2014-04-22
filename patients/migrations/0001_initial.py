# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'SafetyNetRelationship'
        db.create_table(u'patients_safetynetrelationship', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('source_patient', self.gf('django.db.models.fields.related.ForeignKey')(related_name='target_patient_safety_net', to=orm['patients.PatientProfile'])),
            ('target_patient', self.gf('django.db.models.fields.related.ForeignKey')(related_name='source_patient_safety_nets', to=orm['patients.PatientProfile'])),
            ('source_to_target_relationship', self.gf('django.db.models.fields.CharField')(max_length=20)),
            ('target_to_source_relationship', self.gf('django.db.models.fields.CharField')(max_length=20)),
            ('receives_all_reminders', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('opt_out', self.gf('django.db.models.fields.BooleanField')(default=False)),
        ))
        db.send_create_signal(u'patients', ['SafetyNetRelationship'])

        # Adding unique constraint on 'SafetyNetRelationship', fields ['source_patient', 'target_patient']
        db.create_unique(u'patients_safetynetrelationship', ['source_patient_id', 'target_patient_id'])

        # Adding model 'PatientProfile'
        db.create_table(u'patients_patientprofile', (
            (u'userprofile_ptr', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['common.UserProfile'], unique=True, primary_key=True)),
            ('mrn', self.gf('django.db.models.fields.PositiveIntegerField')(default=0)),
            ('age', self.gf('django.db.models.fields.PositiveIntegerField')(default=0)),
            ('gender', self.gf('django.db.models.fields.CharField')(default='', max_length=1)),
            ('height', self.gf('django.db.models.fields.PositiveIntegerField')(default=0)),
            ('height_unit', self.gf('django.db.models.fields.CharField')(default='in', max_length=2)),
            ('weight', self.gf('django.db.models.fields.PositiveIntegerField')(default=0)),
            ('weight_unit', self.gf('django.db.models.fields.CharField')(default='lb', max_length=2)),
            ('enroller', self.gf('django.db.models.fields.related.ForeignKey')(default=None, related_name='enroller', null=True, blank=True, to=orm['common.UserProfile'])),
            ('primary_phone_number', self.gf('django.db.models.fields.CharField')(max_length=32, unique=True, null=True, blank=True)),
            ('email', self.gf('django.db.models.fields.EmailField')(max_length=75, unique=True, null=True, blank=True)),
            ('num_caregivers', self.gf('django.db.models.fields.IntegerField')(default=0)),
            ('primary_contact', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['patients.PatientProfile'], null=True)),
            ('quit_request_datetime', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
        ))
        db.send_create_signal(u'patients', ['PatientProfile'])


    def backwards(self, orm):
        # Removing unique constraint on 'SafetyNetRelationship', fields ['source_patient', 'target_patient']
        db.delete_unique(u'patients_safetynetrelationship', ['source_patient_id', 'target_patient_id'])

        # Deleting model 'SafetyNetRelationship'
        db.delete_table(u'patients_safetynetrelationship')

        # Deleting model 'PatientProfile'
        db.delete_table(u'patients_patientprofile')


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
        }
    }

    complete_apps = ['patients']