# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'Country'
        db.create_table(u'common_country', (
            ('iso_code', self.gf('django.db.models.fields.CharField')(max_length=2, primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=64)),
        ))
        db.send_create_signal(u'common', ['Country'])

        # Adding model 'UserProfile'
        db.create_table(u'common_userprofile', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('password', self.gf('django.db.models.fields.CharField')(max_length=128)),
            ('last_login', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now)),
            ('is_superuser', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('status', self.gf('django.db.models.fields.CharField')(default='n', max_length=2)),
            ('username', self.gf('django.db.models.fields.CharField')(unique=True, max_length=40)),
            ('first_name', self.gf('django.db.models.fields.CharField')(max_length=40)),
            ('last_name', self.gf('django.db.models.fields.CharField')(max_length=40)),
            ('full_name', self.gf('django.db.models.fields.CharField')(max_length=80)),
            ('birthday', self.gf('django.db.models.fields.DateField')(null=True, blank=True)),
            ('is_admin', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('join_datetime', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('is_active', self.gf('django.db.models.fields.BooleanField')(default=True)),
            ('auth_token', self.gf('django.db.models.fields.CharField')(max_length=128)),
            ('auth_token_active', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('auth_token_datetime', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
            ('auth_token_login_attempts', self.gf('django.db.models.fields.IntegerField')(default=0)),
            ('auth_token_last_login_datetime', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
            ('has_password', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('address_line1', self.gf('django.db.models.fields.CharField')(max_length=64)),
            ('address_line2', self.gf('django.db.models.fields.CharField')(max_length=64)),
            ('postal_code', self.gf('django.db.models.fields.CharField')(max_length=10)),
            ('city', self.gf('django.db.models.fields.CharField')(max_length=64)),
            ('state_province', self.gf('django.db.models.fields.CharField')(max_length=64)),
            ('country_iso_code', self.gf('django.db.models.fields.CharField')(max_length=2)),
        ))
        db.send_create_signal(u'common', ['UserProfile'])

        # Adding M2M table for field groups on 'UserProfile'
        m2m_table_name = db.shorten_name(u'common_userprofile_groups')
        db.create_table(m2m_table_name, (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('userprofile', models.ForeignKey(orm[u'common.userprofile'], null=False)),
            ('group', models.ForeignKey(orm[u'auth.group'], null=False))
        ))
        db.create_unique(m2m_table_name, ['userprofile_id', 'group_id'])

        # Adding M2M table for field user_permissions on 'UserProfile'
        m2m_table_name = db.shorten_name(u'common_userprofile_user_permissions')
        db.create_table(m2m_table_name, (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('userprofile', models.ForeignKey(orm[u'common.userprofile'], null=False)),
            ('permission', models.ForeignKey(orm[u'auth.permission'], null=False))
        ))
        db.create_unique(m2m_table_name, ['userprofile_id', 'permission_id'])

        # Adding model 'RegistrationProfile'
        db.create_table(u'common_registrationprofile', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('userprofile', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['common.UserProfile'], unique=True)),
            ('phonenumber_activation_key', self.gf('django.db.models.fields.CharField')(max_length=5)),
            ('email_activation_key', self.gf('django.db.models.fields.CharField')(max_length=40)),
            ('last_touch_datetime', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
        ))
        db.send_create_signal(u'common', ['RegistrationProfile'])

        # Adding model 'Drug'
        db.create_table(u'common_drug', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(unique=True, max_length=64)),
        ))
        db.send_create_signal(u'common', ['Drug'])

        # Adding model 'DrugFact'
        db.create_table(u'common_drugfact', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('drug', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['common.Drug'])),
            ('fact', self.gf('django.db.models.fields.CharField')(max_length=160)),
        ))
        db.send_create_signal(u'common', ['DrugFact'])


    def backwards(self, orm):
        # Deleting model 'Country'
        db.delete_table(u'common_country')

        # Deleting model 'UserProfile'
        db.delete_table(u'common_userprofile')

        # Removing M2M table for field groups on 'UserProfile'
        db.delete_table(db.shorten_name(u'common_userprofile_groups'))

        # Removing M2M table for field user_permissions on 'UserProfile'
        db.delete_table(db.shorten_name(u'common_userprofile_user_permissions'))

        # Deleting model 'RegistrationProfile'
        db.delete_table(u'common_registrationprofile')

        # Deleting model 'Drug'
        db.delete_table(u'common_drug')

        # Deleting model 'DrugFact'
        db.delete_table(u'common_drugfact')


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
        u'common.country': {
            'Meta': {'ordering': "['name', 'iso_code']", 'object_name': 'Country'},
            'iso_code': ('django.db.models.fields.CharField', [], {'max_length': '2', 'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '64'})
        },
        u'common.drug': {
            'Meta': {'object_name': 'Drug'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '64'})
        },
        u'common.drugfact': {
            'Meta': {'object_name': 'DrugFact'},
            'drug': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['common.Drug']"}),
            'fact': ('django.db.models.fields.CharField', [], {'max_length': '160'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        u'common.registrationprofile': {
            'Meta': {'object_name': 'RegistrationProfile'},
            'email_activation_key': ('django.db.models.fields.CharField', [], {'max_length': '40'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_touch_datetime': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'phonenumber_activation_key': ('django.db.models.fields.CharField', [], {'max_length': '5'}),
            'userprofile': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['common.UserProfile']", 'unique': 'True'})
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
        }
    }

    complete_apps = ['common']