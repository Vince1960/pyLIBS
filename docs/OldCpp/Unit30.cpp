//---------------------------------------------------------------------------

#include <vcl.h>
#include <stdio.h>
#include <string.h>
#include <math.h>
#pragma hdrstop
#include "SDIMain.h"
#include "Unit2.h"
#include "Unit5.h"
#include "Unit6.h"
#include "Unit1.h"
#include "Unit77.h"
#define COLORE 12632150
#include "Unit30.h"
//---------------------------------------------------------------------------
#pragma package(smart_init)
#pragma resource "*.dfm"
TForm30 *Form30;
//---------------------------------------------------------------------------
__fastcall TForm30::TForm30(TComponent* Owner)
	: TForm(Owner)
{
}
//---------------------------------------------------------------------------
void __fastcall TForm30::Button1Click(TObject *Sender)
{
FILE *out;
   out = fopen("C:\\libssearch.txt", "w");
 char sqls[300];
 int rc, rc1;
 sprintf(sqls,"SELECT DISTINCT specie FROM datalibs");
  Form30->Query1->SQL->Clear();
 Form30->Query1->SQL->Add(sqls);
 Form30->Query1->Open();
 rc=Form30->Query1->RecordCount;
	Form30->Query1->First();
	for (int i = 0; i < rc; i++) {
  String spc= Form30->Query1->FieldValues["specie"];
	Form30->Query2->SQL->Clear();
	   sprintf(sqls,"SELECT * FROM %s WHERE ion=1", spc);
 Form30->Query2->SQL->Add(sqls);
 Form30->Query2->Open();
	 rc1=Form30->Query2->RecordCount;
	 for (int jj=0; jj < rc1; jj++) {
	  float aki= Form30->Query2->FieldValues["Aki"];
	  float gk= Form30->Query2->FieldValues["gk"];
	  float gi= Form30->Query2->FieldValues["gi"];
	  float ek= Form30->Query2->FieldValues["Ek"];
	  float wave= Form30->Query2->FieldValues["wavelen"];
	  if (gi>0) {
	  float inte=100.*gk/gi*aki*exp(-ek*0.000123985);
	  int ion=1;
	  fprintf(out,"%f %s %f %i\n",wave,spc,inte,ion);
	  }
	  Form30->Query2->Next();
	 }
		Form30->Query2->Close();

     Form30->Query2->SQL->Clear();
	   sprintf(sqls,"SELECT * FROM %s WHERE ion=2", spc);
 Form30->Query2->SQL->Add(sqls);
 Form30->Query2->Open();
	 rc1=Form30->Query2->RecordCount;
	 for (int jj=0; jj < rc1; jj++) {
	  float aki= Form30->Query2->FieldValues["Aki"];
	  float gk= Form30->Query2->FieldValues["gk"];
	  float gi= Form30->Query2->FieldValues["gi"];
	  float ek= Form30->Query2->FieldValues["Ek"];
	  float wave= Form30->Query2->FieldValues["wavelen"];
	  if (gi>0) {
	  float inte=100.*gk/gi*aki*exp(-ek*0.000123985);
	  int ion=2;
	  fprintf(out,"%f %s %f %i\n",wave,spc,inte,ion);
	  }
	  Form30->Query2->Next();
	 }

		Form30->Query2->Close();




	   Form30->Query1->Next();
	}
	Form30->Query1->Close();
	fclose(out);
}
//---------------------------------------------------------------------------
