//---------------------------------------------------------------------------
#include <vcl.h>
#pragma hdrstop
#include <dos.h>
#include <stdio.h>
#include "SDIMain.h"
#include "Unit1.h"
#include "Unit3.h"
#include "Unit4.h"
#include "Unit5.h"
#include "Unit6.h"
#include "Unit7.h"
#include "Unit8.h"
#include "Unit9.h"
#include "Unit10.h"
#include "Unit15.h"
#include "Unit23.h"
#include "Unit26.h"
#include "Unit27.h"
#include "Unit31.h"
#include <math.h>
#include <dir.h>
#define COLORE 12632150

//---------------------------------------------------------------------------
#pragma package(smart_init)
#pragma resource "*.dfm"
TForm6 *Form6;
//---------------------------------------------------------------------------
__fastcall TForm6::TForm6(TComponent* Owner)
        : TForm(Owner)
{
}
//---------------------------------------------------------------------------

void __fastcall TForm6::Button3Click(TObject *Sender)
{
	char stringa[80]="This will clear the current template. Continue?";

if (MessageDlg(stringa, mtConfirmation, TMsgDlgButtons() << mbYes << mbNo << mbCancel, 0) != IDYES) return;

Form6->Table1->Active = false;
//Form6->Query1->Active = false;
Form6->Table1->EmptyTable();
SDIAppForm->Series4->Clear();
Form6->Table1->Active = true;
// Form6->Query1->Active = true;
}
//---------------------------------------------------------------------------

void __fastcall TForm6::Button2Click(TObject *Sender)
{
Form15->Memo1->Text="";
Form15->Show();
}
//---------------------------------------------------------------------------

void __fastcall TForm6::DBGrid1DblClick(TObject *Sender)
{
float range,freq,wdt;
//Form5->Edit1->Text=Form6->Table1->FieldValues["wavelen"];
Form5->Edit1->Text= DBGrid1->Fields[0]->AsString;
range=atof(AnsiString(OKBottomDlg->Edit9->Text).c_str());
 freq=atof(AnsiString(Form5->Edit1->Text).c_str());
Form5->Show();
  SDIAppForm->Chart1->BottomAxis->Automatic=false;
  wdt=20*(atof(AnsiString(OKBottomDlg->Edit14->Text).c_str())+atof(AnsiString(OKBottomDlg->Edit15->Text).c_str()));
SDIAppForm->Chart1->BottomAxis->SetMinMax( freq-wdt, freq+wdt);

float minay,maxay=0;

for (int j=0;j<SDIAppForm->Chart1->SeriesCount();j++)
{

if (SDIAppForm->Chart1->Series[j]->FirstValueIndex > 0)
        {
  for (int pu=SDIAppForm->Chart1->Series[j]->FirstValueIndex;pu <= SDIAppForm->Chart1->Series[j]->LastValueIndex;pu++)
  {
  if (SDIAppForm->Chart1->Series[j]->YValues->Value[pu] > maxay) maxay= SDIAppForm->Chart1->Series[j]->YValues->Value[pu];
  }
        }
}

  SDIAppForm->Chart1->LeftAxis->Automatic=false;

  SDIAppForm->Chart1->LeftAxis->SetMinMax(minay,maxay*1.1);
   SDIAppForm->Chart1->Refresh();
char sqls[300];
sprintf(sqls,"SELECT * FROM datalibs WHERE [wavelen] BETWEEN %f AND %f ORDER BY abs([wavelen]-%f)",(freq-range),(freq+range),freq);
  Form5->Query1->SQL->Clear();
 Form5->Query1->SQL->Add(sqls);
 Form5->Query1->Open();
 Form6->Table1->Refresh();
}
//---------------------------------------------------------------------------

void __fastcall TForm6::Button4Click(TObject *Sender)
{
void showboltz();
showboltz();
}
//---------------------------------------------------------------------------

void __fastcall TForm6::Button6Click(TObject *Sender)
{
void loadtempl(AnsiString nome);
  SDIAppForm->OpenDialog1->Title="Load Template";
 SDIAppForm->OpenDialog1->Filter = "Templates|*.DB";
 SDIAppForm->OpenDialog1->FileName = "*.DB";
 SDIAppForm->OpenDialog1->InitialDir=ExtractFilePath(Application->ExeName)+"Templates";
  if (SDIAppForm->OpenDialog1->Execute())
  {
SDIAppForm->Edit8->Text=SDIAppForm->OpenDialog1->FileName.c_str();
loadtempl(SDIAppForm->OpenDialog1->FileName);
 }
 SDIAppForm->OpenDialog->InitialDir=SDIAppForm->Edit14->Text;
}
//---------------------------------------------------------------------------

void __fastcall TForm6::FormCreate(TObject *Sender)
{
  AnsiString fn=ExtractFilePath(Application->ExeName)+"\Templates\\template.db";
 Form6->Table1->Active = false;
  Form6->Query1->Active = false;
  Table1->DatabaseName = ExtractFilePath(Application->ExeName)+"\Templates";
Table1->TableName = "template.db";
Table1->TableType = ttParadox;
 Table1->EmptyTable();
 SDIAppForm->Series4->Clear();
 Form6->Table1->Active = true;
 Form6->Query1->Active = true;
}
//---------------------------------------------------------------------------





void __fastcall TForm6::DataSource1UpdateData(TObject *Sender)
{
if ((Form6->Table1->FieldByName("specie")->AsString == "") & (Form6->Table1->FieldByName("Aki")->AsFloat != 0.0) & (Form6->Table1->FieldByName("ion")->AsInteger != 0))
{
Form6->Table1->Edit();
Form6->Table1->FieldValues["Aki"]=0.0;
Form6->Table1->FieldValues["ion"]=0;
Form6->Table1->FieldValues["Ek"]=0.0;
Form6->Table1->FieldValues["gk"]=0;
Form6->Table1->FieldValues["gi"]=0;
}

}
//---------------------------------------------------------------------------





void __fastcall TForm6::Table1CalcFields(TDataSet *DataSet)
{
// Table1calcolo->Value=Table1wavelen->Value-1000.0;
}
//---------------------------------------------------------------------------

void __fastcall TForm6::Button1Click(TObject *Sender)
{
	char stringa[80]="This will close the current template. Continue?";
if (MessageDlg(stringa, mtConfirmation, TMsgDlgButtons() << mbYes << mbNo << mbCancel, 0) != IDYES) return;
  AnsiString fn=ExtractFilePath(Application->ExeName)+"\Templates\\template.db";
Form6->Table1->Active=false;
  Form6->Query1->Active=false;
  Form6->Table1->TableType=ttParadox;
  Form6->Table1->TableName=fn;
   Form6->Table1->EmptyTable();
 SDIAppForm->Series4->Clear();
 Form6->Table1->Active = true;
 Form6->Query1->Active = true;
Form6->Caption="Template";
}
//---------------------------------------------------------------------------



void __fastcall TForm6::DBNavigator1BeforeAction(TObject *Sender,
      TNavigateBtn Button)
{
 float wav, wav1;
        if (Button ==  nbDelete)
        {
         int i=Form6->Table1->RecNo;

        SDIAppForm->Series4->Delete(i-1);
     
        }
}
//---------------------------------------------------------------------------
void showboltz()
        {
  int colo[34]={clRed,clGreen,clBlue,clPurple,clGray,clMaroon,clNavy,clOlive,clLtGray,clFuchsia,clWhite,clTeal,clSilver,clLime,clAqua,clBlack+200,clRed+200,clGray+200,clAqua+200,clBlue+200,clGreen+200,clBlack+200,clMaroon+200,clNavy+200,clDkGray+200,clOlive+200,clPurple+200,clLtGray+200,clFuchsia+200,clWhite+200,clTeal+200,clSilver+200,clLime+200};


	 for (int w=1; w<=Form23->StringGrid1->RowCount;w++)
				{
				Form23->StringGrid1->Cells[3][w]="";
				}


        // Carica curva taratura

        Form9->Chart1->ApplyZOrder=false;
        Form9->Chart1->BottomAxis->Automatic=true;
        Form9->Chart1->LeftAxis->Automatic=true;
        if ((OKBottomDlg->CheckBox2->Checked==true))
                {

                float xf,yf;
                Form10->Series1->Active=true;
                Form10->Series1->Clear();
                
                FILE *strm;
				strm = fopen(AnsiString(OKBottomDlg->Edit10->Text).c_str(), "rt");
				do
                        {
                        fscanf(strm,"%g %g", &xf, &yf);
                        if ((OKBottomDlg->CheckBox7->Checked==true) & (xf < 1500.0))
                                {
                                xf=xf*10.0;
                                }
						Form10->Series1->AddXY(xf,yf,' ',clBlack);
                        }
                while(!feof(strm));
				fclose(strm);
				Form10->Series1->AddXY(2000.0,1.0,' ',clBlack);
				Form10->Series1->AddXY(10000.0,1.0,' ',clBlack);
                }
        else
                {
                Form10->Series1->Clear();
				Form10->Series1->AddXY(2000.0,1.0,' ',clBlack);
				Form10->Series1->AddXY(10000.0,1.0,' ',clBlack);
                }
        // Fine caricamento taratura

        // ShowMessage("Inizializza griglia, siamo in form 6");
		float soglia=atof(AnsiString(OKBottomDlg->Edit17->Text).c_str());
        char sqls[300];

        Form9->StringGrid1->RowCount=128;
		Form9->StringGrid2->RowCount=64;
		Form31->Refresh();
		if (Form31->Button3->Caption == "DISABLED") {
        int I, J;
        for (I = 1; I < Form9->StringGrid1->ColCount; I++)
        for (J = 1; J < Form9->StringGrid1->RowCount; J++)
                Form9->StringGrid1->Cells[I][J] = "";
        for (I = 1; I < Form9->StringGrid2->ColCount; I++)
        for (J = 1; J < Form9->StringGrid2->RowCount; J++)
                Form9->StringGrid2->Cells[I][J] = "";
        Form9->ComboBox1->Clear();
		Form9->ComboBox2->Clear();
		}
        while (Form9->Chart1->SeriesCount()>0)
                {
                Form9->Chart1->Series[0]->Free();
                }

        Form9->StringGrid1->ColWidths[0]=20;
        Form9->StringGrid1->Cells[1][0]="Spec.";
        Form9->StringGrid1->Cells[2][0]="Lines";
        Form9->StringGrid1->Cells[3][0]="kT";
        Form9->StringGrid1->Cells[4][0]="q";
        Form9->StringGrid1->Cells[5][0]="Z(T)";

		sprintf(sqls,"SELECT DISTINCT SPECIE,ION FROM %s WHERE aki != 0.0 AND aki != -1.0 AND inte > 0.0 ORDER BY specie,ion",AnsiString(ExtractFileName(Form6->Table1->TableName)).c_str());
		Form9->Query1->Active=false;
        Form9->Query1->DatabaseName=ExtractFilePath(Form6->Table1->TableName);
        Form9->Query1->Active=true;
        Form9->Query1->SQL->Clear();

        Form9->Query1->SQL->Add(sqls);
        Form9->Query1->Open();
        Form9->Query1->First();
        Form9->Query2->Active=false;
        Form9->Query2->DatabaseName=ExtractFilePath(Form6->Table1->TableName);
        Form9->Query2->Active=true;
		sprintf(sqls,"SELECT DISTINCT SPECIE FROM %s WHERE aki != 0.0 AND aki !=-1.0 AND inte > 0.0 ORDER BY specie",AnsiString(ExtractFileName(Form6->Table1->TableName)).c_str());
		Form9->Query2->SQL->Clear();

        Form9->Query2->SQL->Add(sqls);
        Form9->Query2->Open();
        Form9->Query2->First();

        Form9->StringGrid2->ColWidths[0]=20;
        Form9->StringGrid2->Cells[1][0]="Elem.";
        Form9->StringGrid2->Cells[2][0]="Num %";
        Form9->StringGrid2->Cells[3][0]="Mass %";
        Form9->StringGrid2->Cells[4][0]="Ne";
        Form9->StringGrid2->Cells[5][0]="I/(I+II)";

        for (int rcu=0; rcu < Form9->Query2->RecordCount;rcu++)
                {
				Form9->Edit3->Text=Form9->Query2->FieldByName("specie")->AsString;
                Form9->StringGrid2->Cells[1][rcu+1]=Form9->Edit3->Text;
                Form9->ComboBox2->Items->Add(Form9->Edit3->Text);
                Form9->Query2->Next();
                }
        Form9->Query2->First();
        Form9->Query1->First();

		char sname[4];
        for (int i=0; i < Form9->Query1->RecordCount; i++)
                {
                TPointSeries *MySeries = new TPointSeries(Form9);
                MySeries->XValues->Order = loNone;
                MySeries->ParentChart=Form9->Chart1;

				Form9->Edit3->Text=Form9->Query1->FieldByName("specie")->AsString;
				Form9->Edit4->Text=Form9->Query1->FieldByName("ion")->AsString;
				int ioniz=Form9->Query1->FieldByName("ion")->AsInteger;
                switch(ioniz)
                        {
                        case 1:
						sprintf(sname,"%sI",AnsiString(Trim(Form9->Edit3->Text)).c_str());
						break;
						case 2:
						sprintf(sname,"%sII",AnsiString(Trim(Form9->Edit3->Text)).c_str());
                        break;
						}
				Form9->StringGrid1->Cells[1][i+1]=sname;
                Form9->ComboBox1->Items->Add(sname);
                Form9->Query3->Active=false;
                Form9->Query3->DatabaseName=ExtractFilePath(Form6->Table1->TableName);

                Form9->Query3->Active=true;
                Form9->Query6->Active=false;
                Form9->Query6->DatabaseName=ExtractFilePath(Form6->Table1->TableName);
                Form9->Query6->Active=true;
				MySeries->Name=sname;
				MySeries->Cursor=crHandPoint;

				sprintf(sqls,"SELECT * FROM %s WHERE specie='%s' AND ion=%s AND aki != 0.0 AND aki !=-1.0 AND inte > 0.0",AnsiString(ExtractFileName(Form6->Table1->TableName)).c_str(),AnsiString(Form9->Edit3->Text).c_str(),Form9->Edit4->Text);
				Form9->Query3->SQL->Clear();
                Form9->Query3->DatabaseName=ExtractFilePath(Form6->Table1->TableName);
                Form9->Query3->SQL->Add(sqls);
                Form9->Query3->Open();
				Form9->Query3->First();
				Form9->StringGrid1->Cells[2][i+1]=Form9->Query3->RecordCount;
                for (int j=0; j < Form9->Query3->RecordCount; j++)
                        {
                        float wave=Form9->Query3->FieldValues["wavelen"];
                        float inte=Form9->Query3->FieldValues["inte"];
                        float erro=Form9->Query3->FieldValues["error-inte"];
                        float aki= Form9->Query3->FieldValues["aki"];
                        int gk= Form9->Query3->FieldValues["gk"];
                        float Ek= Form9->Query3->FieldValues["Ek"]*1.23985e-4;
                        float yyy;

                        if (OKBottomDlg->CheckBox2->Checked==true && OKBottomDlg->RadioButton2->Checked==true)
                                {
                                for (int k=0; k < Form10->Series1->Count(); k++)
                                        {
                                        if (wave < Form10->Series1->XValues->Value[k])
                                                {
                                                yyy=Form10->Series1->YValues->Value[k]+
                                                (Form10->Series1->YValues->Value[k-1]-Form10->Series1->YValues->Value[k])/
                                                (Form10->Series1->XValues->Value[k-1]-Form10->Series1->XValues->Value[k])*
                                                (wave-Form10->Series1->XValues->Value[k]);
                                                goto aaa;
                                                }
                                        }
                                }
                        else
                                {
                                yyy=1.0;
                                }
						aaa:
						if (Form31->Button3->Caption=="ENABLED") {
							   float ass=StrToFloat(Form9->StringGrid1->Cells[4][i+1]);
						 for (int ii = 1; ii < Form31->StringGrid1->RowCount; ii++) {
						  if (Form31->StringGrid1->Cells[1][ii] == Form9->Edit3->Text) {

						  float csp= StrToFloat(Form31->StringGrid1->Cells[3][ii].c_str());
						  float cs= StrToFloat(Form31->StringGrid1->Cells[2][ii].c_str());
						  float tt=StrToFloat(Form9->Edit1->Text);


						  float yp=-Ek/tt+ass+log(csp/cs);
						  float delta=yp-log(inte/yyy/fabs(aki*gk));
							  yyy*=exp(-delta);
						  }
						 }
						}

						inte/=yyy;
						erro/=yyy;
						Form9->Chart1->Series[i]->Active=true;

						float yy=log(inte/fabs(aki*gk));
                        // float erl=erro/inte;
                        float erl=0.1;
                        char wa[20];
                        sprintf(wa,"%4.2e",erl);

                        if (aki > soglia)
                                {
                                Form9->Chart1->Series[i]->SeriesColor=colo[i];
                                Form9->Chart1->Series[i]->AddXY(Ek,yy,wa,clTeeColor);
                                }
                        else
                                {
                                Form9->Chart1->Series[i]->AddXY(Ek,yy,wa,COLORE);
                                }

                        Form9->Query3->Next();
                        }
                Form9->Query1->Next();
                }
        Form9->Query1->First();
        Form9->Show();
        }
//---------------------------------------------------------------------------



void __fastcall TForm6::Button7Click(TObject *Sender)
{
Form3->Show();
}
//---------------------------------------------------------------------------

void __fastcall TForm6::Button8Click(TObject *Sender)
{
Table1->ApplyUpdates();
}
//---------------------------------------------------------------------------
 void showsboltz()
        {
  int colo[34]={clRed,clGreen,clBlue,clPurple,clGray,clMaroon,clNavy,clOlive,clLtGray,clFuchsia,clWhite,clTeal,clSilver,clLime,clAqua,clBlack+200,clRed+200,clGray+200,clAqua+200,clBlue+200,clGreen+200,clBlack+200,clMaroon+200,clNavy+200,clDkGray+200,clOlive+200,clPurple+200,clLtGray+200,clFuchsia+200,clWhite+200,clTeal+200,clSilver+200,clLime+200};

        for (int w=1; w<=Form23->StringGrid1->RowCount;w++)
                {
                Form23->StringGrid1->Cells[3][w]="";
                }

                  for (int w=1; w<=Form27->StringGrid2->RowCount;w++)
                {
                Form27->StringGrid2->Cells[1][w]="";
                Form27->StringGrid2->Cells[2][w]="";
                Form27->StringGrid2->Cells[3][w]="";
      //          Form27->StringGrid2->Cells[4][w]="";
                }

        // Carica curva taratura

        Form9->Chart1->ApplyZOrder=false;
        Form9->Chart1->BottomAxis->Automatic=true;
        Form9->Chart1->LeftAxis->Automatic=true;
        if ((OKBottomDlg->CheckBox2->Checked==true))
                {

                float xf,yf;
                Form10->Series1->Active=true;
                Form10->Series1->Clear();

                FILE *strm;
				strm = fopen(AnsiString(OKBottomDlg->Edit10->Text).c_str(), "rt");
                do
                        {
                        fscanf(strm,"%g %g", &xf, &yf);
                        if ((OKBottomDlg->CheckBox7->Checked==true) & (xf < 1500.0))
                                {
                                xf=xf*10.0;
                                }
						Form10->Series1->AddXY(xf,yf,' ',clBlack);
                        }
                while(!feof(strm));
				fclose(strm);
				Form10->Series1->AddXY(2000.0,1.0,' ',clBlack);
				Form10->Series1->AddXY(10000.0,1.0,' ',clBlack);
                }
        else
                {
                Form10->Series1->Clear();
                Form10->Series1->AddXY(2000.0,1.0,' ',clBlack);
                Form10->Series1->AddXY(10000.0,1.0,' ',clBlack);
                }
        // Fine caricamento taratura

        //ShowMessage("Inizializza griglia, siamo in form 6");
		float soglia=atof(AnsiString(OKBottomDlg->Edit17->Text).c_str());
        char sqls[300];

        Form9->StringGrid1->RowCount=128;
        Form9->StringGrid2->RowCount=64;

        int I, J;
        for (I = 1; I < Form9->StringGrid1->ColCount; I++)
        for (J = 1; J < Form9->StringGrid1->RowCount; J++)
                Form9->StringGrid1->Cells[I][J] = "";
        for (I = 1; I < Form9->StringGrid2->ColCount; I++)
        for (J = 1; J < Form9->StringGrid2->RowCount; J++)
                Form9->StringGrid2->Cells[I][J] = "";
        Form9->ComboBox1->Clear();
        Form9->ComboBox2->Clear();
        while (Form9->Chart1->SeriesCount()>0)
                {
                Form9->Chart1->Series[0]->Free();
                }
           while (Form27->Chart1->SeriesCount()>0)
                {
                Form27->Chart1->Series[0]->Free();
                }
        Form9->StringGrid1->ColWidths[0]=20;
        Form9->StringGrid1->Cells[1][0]="Spec.";
        Form9->StringGrid1->Cells[2][0]="Lines";
        Form9->StringGrid1->Cells[3][0]="kT";
        Form9->StringGrid1->Cells[4][0]="q";
        Form9->StringGrid1->Cells[5][0]="Z(T)";

		sprintf(sqls,"SELECT DISTINCT SPECIE,ION FROM %s WHERE aki != 0.0 AND aki != -1.0 AND inte > 0.0 ORDER BY specie,ion",AnsiString(ExtractFileName(Form6->Table1->TableName)).c_str());
        Form9->Query1->Active=false;
        Form9->Query1->DatabaseName=ExtractFilePath(Form6->Table1->TableName);
        Form9->Query1->Active=true;
        Form9->Query1->SQL->Clear();

        Form9->Query1->SQL->Add(sqls);
        Form9->Query1->Open();
        Form9->Query1->First();
        Form9->Query2->Active=false;
        Form9->Query2->DatabaseName=ExtractFilePath(Form6->Table1->TableName);
        Form9->Query2->Active=true;
		sprintf(sqls,"SELECT DISTINCT SPECIE FROM %s WHERE aki != 0.0 AND aki !=-1.0 AND inte > 0.0 ORDER BY specie",AnsiString(ExtractFileName(Form6->Table1->TableName)).c_str());
        Form9->Query2->SQL->Clear();

        Form9->Query2->SQL->Add(sqls);
        Form9->Query2->Open();
        Form9->Query2->First();

        Form9->StringGrid2->ColWidths[0]=20;
        Form9->StringGrid2->Cells[1][0]="Elem.";
        Form9->StringGrid2->Cells[2][0]="Num %";
        Form9->StringGrid2->Cells[3][0]="Mass %";
        Form9->StringGrid2->Cells[4][0]="Ne";
        Form9->StringGrid2->Cells[5][0]="I/(I+II)";

        for (int rcu=0; rcu < Form9->Query2->RecordCount;rcu++)
                {
                Form9->Edit3->Text=Form9->Query2->FieldByName("specie")->AsString;
                Form9->StringGrid2->Cells[1][rcu+1]=Form9->Edit3->Text;
                Form9->ComboBox2->Items->Add(Form9->Edit3->Text);
                Form9->Query2->Next();
                }
        Form9->Query2->First();
        Form9->Query1->First();

        char sname[32];
        for (int i=0; i < Form9->Query1->RecordCount; i++)
                {
                TPointSeries *MySeries = new TPointSeries(Form9);
                MySeries->XValues->Order = loNone;
                MySeries->ParentChart=Form9->Chart1;

                Form9->Edit3->Text=Form9->Query1->FieldByName("specie")->AsString;
                Form9->Edit4->Text=Form9->Query1->FieldByName("ion")->AsString;
                int ioniz=Form9->Query1->FieldByName("ion")->AsInteger;
                switch(ioniz)
                        {
                        case 1:
                        sprintf(sname,"%sI",Trim(Form9->Edit3->Text));
                        break;
                        case 2:
                        sprintf(sname,"%sII",Trim(Form9->Edit3->Text));
                        break;
                        }
                Form9->StringGrid1->Cells[1][i+1]=sname;
                Form9->ComboBox1->Items->Add(sname);
                Form9->Query3->Active=false;
                Form9->Query3->DatabaseName=ExtractFilePath(Form6->Table1->TableName);

                Form9->Query3->Active=true;
                Form9->Query6->Active=false;
                Form9->Query6->DatabaseName=ExtractFilePath(Form6->Table1->TableName);
                Form9->Query6->Active=true;
                MySeries->Name=sname;
                MySeries->Cursor=crHandPoint;

				sprintf(sqls,"SELECT * FROM %s WHERE specie='%s' AND ion=%s AND aki != 0.0 AND aki !=-1.0 AND inte > 0.0",AnsiString(ExtractFileName(Form6->Table1->TableName)).c_str(),Form9->Edit3->Text,Form9->Edit4->Text);
                Form9->Query3->SQL->Clear();
                Form9->Query3->DatabaseName=ExtractFilePath(Form6->Table1->TableName);
                Form9->Query3->SQL->Add(sqls);
                Form9->Query3->Open();
                Form9->Query3->First();
                Form9->StringGrid1->Cells[2][i+1]=Form9->Query3->RecordCount;
                for (int j=0; j < Form9->Query3->RecordCount; j++)
                        {
                        float wave=Form9->Query3->FieldValues["wavelen"];
                        float inte=Form9->Query3->FieldValues["inte"];
                        float erro=Form9->Query3->FieldValues["error-inte"];
                        float aki= Form9->Query3->FieldValues["aki"];
                        int gk= Form9->Query3->FieldValues["gk"];
                        float Ek= Form9->Query3->FieldValues["Ek"]*1.23985e-4;
                        float yyy;

                        if (OKBottomDlg->CheckBox2->Checked==true && OKBottomDlg->RadioButton2->Checked==true)
                                {
                                for (int k=0; k < Form10->Series1->Count(); k++)
                                        {
                                        if (wave < Form10->Series1->XValues->Value[k])
                                                {
                                                yyy=Form10->Series1->YValues->Value[k]+
                                                (Form10->Series1->YValues->Value[k-1]-Form10->Series1->YValues->Value[k])/
                                                (Form10->Series1->XValues->Value[k-1]-Form10->Series1->XValues->Value[k])*
                                                (wave-Form10->Series1->XValues->Value[k]);
                                                goto aaa;
                                                }
                                        }
                                }
                        else
                                {
                                yyy=1.0;
                                }
                        aaa:
                        inte/=yyy;
                        erro/=yyy;
                        Form9->Chart1->Series[i]->Active=true;

                        float yy=log(inte/fabs(aki*gk));
                        // float erl=erro/inte;
                        float erl=0.1;
                        char wa[20];
                        sprintf(wa,"%4.2e",erl);

                        if (aki > soglia)
                                {
                                Form9->Chart1->Series[i]->SeriesColor=colo[i];
                                Form9->Chart1->Series[i]->AddXY(Ek,yy,wa,clTeeColor);
                                }
                        else
                                {
                                Form9->Chart1->Series[i]->AddXY(Ek,yy,wa,COLORE);
                                }

                        Form9->Query3->Next();
                        }
                Form9->Query1->Next();
                }
        Form9->Query1->First();

       // Cerca neutro e ionizzato

       Form27->StringGrid2->ColWidths[0]=20;
       Form27->StringGrid2->ColWidths[1]=30;
       Form27->StringGrid2->ColWidths[2]=50;
       Form27->StringGrid2->ColWidths[3]=50;
        Form27->StringGrid2->Cells[1][0]="Elem.";
        Form27->StringGrid2->Cells[2][0]="q";
        Form27->StringGrid2->Cells[3][0]="kT";

   //     Form27->StringGrid2->Cells[4][0]="Ne";


		sprintf(sqls,"SELECT DISTINCT specie FROM %s WHERE aki != 0.0 AND aki != -1.0 AND inte > 0.0  ORDER BY specie",AnsiString(ExtractFileName(Form6->Table1->TableName)).c_str(),soglia);
        Form9->Query2->SQL->Clear();
        Form9->Query2->SQL->Add(sqls);
        Form9->Query2->Open();
        Form9->Query2->First();

        double saha,eion;
        int jj=0;
        for (int i=0; i < Form9->Query2->RecordCount;i++)
                {
                // Cerco stato neutro
                //ShowMessage(i);
                AnsiString ppp=Form9->Query2->FieldValues["specie"];
				sprintf(sqls,"SELECT * FROM %s WHERE specie='%s' AND ion=1 AND aki >0 AND inte > 0.0",AnsiString(ExtractFileName(Form6->Table1->TableName)).c_str(),ppp);
                Form9->Query6->SQL->Clear();
                Form9->Query6->SQL->Add(sqls);
                Form9->Query6->Open();
                Form9->Query6->First();
                int lin1=Form9->Query6->RecordCount;

				sprintf(sname,"%sI",AnsiString(Trim(ppp)).c_str());

                // Cerco stato ionizzato

				sprintf(sqls,"SELECT * FROM %s WHERE specie='%s' AND ion=2 AND aki >0 AND inte > 0.0",AnsiString(ExtractFileName(Form6->Table1->TableName)).c_str(),ppp);
                Form9->Query3->SQL->Clear();
                Form9->Query3->SQL->Add(sqls);
                Form9->Query3->Open();
                Form9->Query3->First();
                int lin2=Form9->Query3->RecordCount;
				sprintf(sname,"%sII",AnsiString(Trim(ppp)).c_str());

                // Se ci sono I e II calcolo tutti i rapporti
                if ((lin1*lin2) !=0)
                        {
                        sprintf(sqls,"SELECT * FROM elementi WHERE [specie]='%s'",Form9->StringGrid2->Cells[1][i+1]);
                        Form9->Query5->SQL->Clear();
                        Form9->Query5->SQL->Add(sqls);
                        Form9->Query5->Open();
                        eion=Form9->Query5->FieldValues["en_ion"]*1.23985e-4;
                        jj++;
                         Form27->StringGrid2->Cells[1][jj]=Form9->StringGrid2->Cells[1][i+1];


                         TPointSeries *MySeries = new TPointSeries(Form27);
                           MySeries->XValues->Order = loNone;
                            MySeries->ParentChart=Form27->Chart1;
                             MySeries->Name=Form27->StringGrid2->Cells[1][jj];
                              MySeries->Cursor=crHandPoint;

                       Form9->Query6->First();
                       float inte1,inte2,e1,e2,gi1,gi2,gk1,gk2,ekk,ratio;
                       for (int i=0; i <=lin1;i++)
                        {
                        float wave=Form9->Query6->FieldValues["wavelen"];
                        float gi1=Form9->Query6->FieldValues["gi"];
                        float gk1=Form9->Query6->FieldValues["gk"];
                        float inte1=Form9->Query6->FieldValues["inte"];
                        float ak1=Form9->Query6->FieldValues["aki"];
                        float e1= Form9->Query6->FieldValues["Ek"]*1.23985e-4;
                        float yyy=1.0;

                        if (OKBottomDlg->CheckBox2->Checked==true && OKBottomDlg->RadioButton2->Checked==true)
                                {
                                for (int k=0; k < Form10->Series1->Count(); k++)
                                        {
                                        if (wave < Form10->Series1->XValues->Value[k])
                                                {
                                                yyy=Form10->Series1->YValues->Value[k]+
                                                (Form10->Series1->YValues->Value[k-1]-Form10->Series1->YValues->Value[k])/
                                                (Form10->Series1->XValues->Value[k-1]-Form10->Series1->XValues->Value[k])*
                                                (wave-Form10->Series1->XValues->Value[k]);
                                                break;
                                                }
                                        }
                                }
                        else
                                {
                                yyy=1.0;
                                }
                        
                        inte1/=yyy;


                         Form9->Query3->First();
                         for (int j=0; j <=lin2;j++)
                            {
                            float wave=Form9->Query3->FieldValues["wavelen"];
                        float inte2=Form9->Query3->FieldValues["inte"];
                        float gi2=Form9->Query3->FieldValues["gi"];
                        float gk2=Form9->Query3->FieldValues["gk"];
                        float ak2=Form9->Query3->FieldValues["aki"];
                        float e2= Form9->Query3->FieldValues["Ek"]*1.23985e-4;
                        float yyy;

                        if (OKBottomDlg->CheckBox2->Checked==true && OKBottomDlg->RadioButton2->Checked==true)
                                {
                                for (int k=0; k < Form10->Series1->Count(); k++)
                                        {
                                        if (wave < Form10->Series1->XValues->Value[k])
                                                {
                                                yyy=Form10->Series1->YValues->Value[k]+
                                                (Form10->Series1->YValues->Value[k-1]-Form10->Series1->YValues->Value[k])/
                                                (Form10->Series1->XValues->Value[k-1]-Form10->Series1->XValues->Value[k])*
                                                (wave-Form10->Series1->XValues->Value[k]);
                                                break;
                                                }
                                        }
                                }
                        else
                                {
                                yyy=1.0;
                                }

                        inte2/=yyy;

                             ratio=-log(inte1/gk1/ak1)+log(inte2/gk2/ak2);
                             ekk=eion-e1+e2;
                             MySeries->AddXY(ekk,ratio);
                             Form9->Query3->Next();
                            }
                          Form9->Query6->Next();
                        }

                        int kti=1;

                   }
                Form9->Query2->Next();
                }


           Form27->Show();

        }
//---------------------------------------------------------------------------
 void showsahaboltz()
        {
   int colo[34]={clRed,clGreen,clBlue,clPurple,clGray,clMaroon,clNavy,clOlive,clLtGray,clFuchsia,clWhite,clTeal,clSilver,clLime,clAqua,clBlack+200,clRed+200,clGray+200,clAqua+200,clBlue+200,clGreen+200,clBlack+200,clMaroon+200,clNavy+200,clDkGray+200,clOlive+200,clPurple+200,clLtGray+200,clFuchsia+200,clWhite+200,clTeal+200,clSilver+200,clLime+200};

        // Carica curva taratura

      Form9->Chart1->ApplyZOrder=false;
        Form9->Chart1->BottomAxis->Automatic=true;
        Form9->Chart1->LeftAxis->Automatic=true;
        if ((OKBottomDlg->CheckBox2->Checked==true))
                {

                float xf,yf;
                Form10->Series1->Active=true;
                Form10->Series1->Clear();

                FILE *strm;
				strm = fopen(AnsiString(OKBottomDlg->Edit10->Text).c_str(), "rt");
                do
                        {
                        fscanf(strm,"%g %g", &xf, &yf);
                        if ((OKBottomDlg->CheckBox7->Checked==true) & (xf < 1500.0))
                                {
                                xf=xf*10.0;
                                }
						Form10->Series1->AddXY(xf,yf,' ',clBlack);
                        }
                while(!feof(strm));
				fclose(strm);
				 Form10->Series1->AddXY(2000.0,1.0,' ',clBlack);
				Form10->Series1->AddXY(10000.0,1.0,' ',clBlack);
                }
        else
                {
                Form10->Series1->Clear();
				Form10->Series1->AddXY(2000.0,1.0,' ',clBlack);
				Form10->Series1->AddXY(10000.0,1.0,' ',clBlack);
				}
        // Fine caricamento taratura


		float soglia=atof(AnsiString(OKBottomDlg->Edit17->Text).c_str());
        char sqls[300];char sname[32];

        Form9->StringGrid1->RowCount=128;
       Form9->StringGrid2->RowCount=64;

        int I, J;
        for (I = 1; I < Form9->StringGrid1->ColCount; I++)
        for (J = 1; J < Form9->StringGrid1->RowCount; J++)
                Form9->StringGrid1->Cells[I][J] = "";
        for (I = 1; I < Form9->StringGrid2->ColCount; I++)
        for (J = 1; J < Form9->StringGrid2->RowCount; J++)
                Form9->StringGrid2->Cells[I][J] = "";
        Form9->ComboBox1->Clear();
        Form9->ComboBox2->Clear();
        while (Form9->Chart1->SeriesCount()>0)
                {
                Form9->Chart1->Series[0]->Free();
                }

           while (Form27->Chart1->SeriesCount()>0)
                {
                Form27->Chart1->Series[0]->Free();
                }

        Form9->StringGrid1->ColWidths[0]=20;
        Form9->StringGrid1->Cells[1][0]="Spec.";
        Form9->StringGrid1->Cells[2][0]="Lines";
        Form9->StringGrid1->Cells[3][0]="kT";
        Form9->StringGrid1->Cells[4][0]="q";
        Form9->StringGrid1->Cells[5][0]="Z(T)";

		sprintf(sqls,"SELECT DISTINCT SPECIE,ION FROM %s WHERE aki != 0.0 AND aki != -1.0 AND inte > 0.0 ORDER BY specie,ion",AnsiString(ExtractFileName(Form6->Table1->TableName)).c_str());
		Form9->Query1->Active=false;
		Form9->Query1->DatabaseName=ExtractFilePath(Form6->Table1->TableName);
        Form9->Query1->Active=true;
        Form9->Query1->SQL->Clear();

        Form9->Query1->SQL->Add(sqls);
        Form9->Query1->Open();
        Form9->Query1->First();
        Form9->Query2->Active=false;
        Form9->Query2->DatabaseName=ExtractFilePath(Form6->Table1->TableName);
        Form9->Query2->Active=true;
		sprintf(sqls,"SELECT DISTINCT SPECIE FROM %s WHERE aki != 0.0 AND aki !=-1.0 AND inte > 0.0 ORDER BY specie",AnsiString(ExtractFileName(Form6->Table1->TableName)).c_str());
		Form9->Query2->SQL->Clear();

        Form9->Query2->SQL->Add(sqls);
        Form9->Query2->Open();
        Form9->Query2->First();

        Form9->StringGrid2->ColWidths[0]=20;
		Form9->StringGrid2->Cells[1][0]="Elem.";
        Form9->StringGrid2->Cells[2][0]="Num %";
        Form9->StringGrid2->Cells[3][0]="Mass %";
        Form9->StringGrid2->Cells[4][0]="Ne";
        Form9->StringGrid2->Cells[5][0]="I/(I+II)";


		for (int rcu=0; rcu < Form9->Query2->RecordCount;rcu++)
                {
                Form9->Edit3->Text=Form9->Query2->FieldByName("specie")->AsString;
                Form9->StringGrid2->Cells[1][rcu+1]=Form9->Edit3->Text;
                Form9->ComboBox2->Items->Add(Form9->Edit3->Text);
                Form9->Query2->Next();
                }
        Form9->Query2->First();
        Form9->Query1->First();


        for (int i=0; i < Form9->Query1->RecordCount; i++)
                {
                TPointSeries *MySeries = new TPointSeries(Form9);
                MySeries->XValues->Order = loNone;
                MySeries->ParentChart=Form9->Chart1;

				Form9->Edit3->Text=Form9->Query1->FieldByName("specie")->AsString;
				Form9->Edit4->Text=Form9->Query1->FieldByName("ion")->AsString;
				int ioniz=Form9->Query1->FieldByName("ion")->AsInteger;

                switch(ioniz)
                        {
                        case 1:
						sprintf(sname,"%sI",AnsiString(Trim(Form9->Edit3->Text).c_str()));
                        break;
                        case 2:
						sprintf(sname,"%sII",AnsiString(Trim(Form9->Edit3->Text).c_str()));
                        break;
						}

				Form9->StringGrid1->Cells[1][i+1]=sname;

				Form9->ComboBox1->Items->Add(sname);
                Form9->Query3->Active=false;
                Form9->Query3->DatabaseName=ExtractFilePath(Form6->Table1->TableName);

                Form9->Query3->Active=true;
                Form9->Query6->Active=false;
                Form9->Query6->DatabaseName=ExtractFilePath(Form6->Table1->TableName);
                Form9->Query6->Active=true;
                MySeries->Name=sname;
				MySeries->Cursor=crHandPoint;

				sprintf(sqls,"SELECT * FROM %s WHERE specie='%s' AND ion=%s AND aki != 0.0 AND aki !=-1.0 AND inte > 0.0",AnsiString(ExtractFileName(Form6->Table1->TableName)).c_str(),Form9->Edit3->Text,Form9->Edit4->Text);
                Form9->Query3->SQL->Clear();
                Form9->Query3->DatabaseName=ExtractFilePath(Form6->Table1->TableName);
                Form9->Query3->SQL->Add(sqls);
                Form9->Query3->Open();
                Form9->Query3->First();
                Form9->StringGrid1->Cells[2][i+1]=Form9->Query3->RecordCount;
                for (int j=0; j < Form9->Query3->RecordCount; j++)
                        {
                        float wave=Form9->Query3->FieldValues["wavelen"];
                        float asswave=Form9->Query3->FieldValues["asswavelen"];
                        float inte=Form9->Query3->FieldValues["inte"];
                        float erro=Form9->Query3->FieldValues["error-inte"];
                        float aki= Form9->Query3->FieldValues["aki"];
                        int gk= Form9->Query3->FieldValues["gk"];
                        float Ek= Form9->Query3->FieldValues["Ek"]*1.23985e-4;
                        float yyy;

                        if (OKBottomDlg->CheckBox2->Checked==true && OKBottomDlg->RadioButton2->Checked==true)
                                {
                                for (int k=0; k < Form10->Series1->Count(); k++)
                                        {
                                        if (wave < Form10->Series1->XValues->Value[k])
                                                {
                                                yyy=Form10->Series1->YValues->Value[k]+
                                                (Form10->Series1->YValues->Value[k-1]-Form10->Series1->YValues->Value[k])/
                                                (Form10->Series1->XValues->Value[k-1]-Form10->Series1->XValues->Value[k])*
                                                (wave-Form10->Series1->XValues->Value[k]);
                                                goto aaa;
                                                }
                                        }
                                }
                        else
                                {
                                yyy=1.0;
                                }
                        aaa:

						 float sac=0;
                           for (int z=1; z < Form23->StringGrid1->RowCount;z++)
                             {
								if (fabs(atof(AnsiString(Form23->StringGrid1->Cells[2][z]).c_str())-asswave)<0.04)
                                {
								 sac=atof(AnsiString(Form23->StringGrid1->Cells[3][z]).c_str());
                                 break;
                                }
                                }
                              if (sac==0) sac=1;

                       inte/=(yyy*sac);
                        erro/=yyy;
                        Form9->Chart1->Series[i]->Active=true;

                        float yy=log(inte/fabs(aki*gk));
                        // float erl=erro/inte;
                        float erl=0.1;
						char wa[20];
                        sprintf(wa,"%4.2e",erl);

                        if (aki > soglia)
                                {
                                Form9->Chart1->Series[i]->SeriesColor=colo[i];
                                Form9->Chart1->Series[i]->AddXY(Ek,yy,wa,clTeeColor);
                                }
                        else
                                {
                                Form9->Chart1->Series[i]->AddXY(Ek,yy,wa,COLORE);
                                }

                        Form9->Query3->Next();
                        }
                Form9->Query1->Next();
                }
        Form9->Query1->First();

       // Cerca neutro e ionizzato


       Form27->StringGrid2->ColWidths[0]=20;
       Form27->StringGrid2->ColWidths[1]=50;
       Form27->StringGrid2->ColWidths[2]=50;
       Form27->StringGrid2->ColWidths[3]=50;
        Form27->StringGrid2->Cells[1][0]="Elem.";
        Form27->StringGrid2->Cells[2][0]="q";
        Form27->StringGrid2->Cells[3][0]="kT";


		sprintf(sqls,"SELECT DISTINCT specie FROM %s WHERE aki != 0.0 AND aki != -1.0 AND inte > 0.0  ORDER BY specie",AnsiString(ExtractFileName(Form6->Table1->TableName)).c_str(),soglia);
        Form9->Query2->SQL->Clear();
        Form9->Query2->SQL->Add(sqls);
        Form9->Query2->Open();
        Form9->Query2->First();

        double saha,eion;
        int jj=0;
        for (int i=0; i < Form9->Query2->RecordCount;i++)
                {
                // Cerco stato neutro

                AnsiString ppp=Form9->Query2->FieldValues["specie"];
				sprintf(sqls,"SELECT * FROM %s WHERE specie='%s' AND ion=1 AND aki >0 AND inte > 0.0",AnsiString(ExtractFileName(Form6->Table1->TableName)).c_str(),ppp);
				Form9->Query6->SQL->Clear();
                Form9->Query6->SQL->Add(sqls);
                Form9->Query6->Open();
                Form9->Query6->First();
                int lin1=Form9->Query6->RecordCount;

				sprintf(sname,"%sI",AnsiString(Trim(ppp)).c_str());

                // Cerco stato ionizzato

                sprintf(sqls,"SELECT * FROM %s WHERE specie='%s' AND ion=2 AND aki >0 AND inte > 0.0",AnsiString(ExtractFileName(Form6->Table1->TableName)).c_str(),ppp);
                Form9->Query3->SQL->Clear();
                Form9->Query3->SQL->Add(sqls);
                Form9->Query3->Open();
                Form9->Query3->First();
                int lin2=Form9->Query3->RecordCount;
				sprintf(sname,"%sII",AnsiString(Trim(ppp)).c_str());

                // Se ci sono I e II calcolo tutti i rapporti

                        {

						sprintf(sqls,"SELECT * FROM elementi WHERE [specie]='%s'",AnsiString(Form9->StringGrid2->Cells[1][i+1]).c_str());
						Form9->Query5->SQL->Clear();
						Form9->Query5->SQL->Add(sqls);
						Form9->Query5->Open();

						float eion=Form9->Query5->FieldValues["en_ion"]*1.23985e-4;

                        jj++;
                         Form27->StringGrid2->Cells[1][jj]=Form9->StringGrid2->Cells[1][i+1];
                         
                         TPointSeries *MySeries = new TPointSeries(Form27);
                           MySeries->XValues->Order = loNone;
                            MySeries->ParentChart=Form27->Chart1;
                             MySeries->Name=Form27->StringGrid2->Cells[1][jj];
                              MySeries->Cursor=crHandPoint;

                   float sac;
                 if (lin1 !=0)
                     {
                       Form9->Query6->First();
                       float inte1,inte2,e1,e2,gi1,gi2,gk1,gk2,ekk,ratio;
                       for (int i=0; i <=lin1;i++)
                        {
                        float wave=Form9->Query6->FieldValues["wavelen"];
                        float asswave=Form9->Query6->FieldValues["asswavelen"];
                        float gi1=Form9->Query6->FieldValues["gi"];
                        float gk1=Form9->Query6->FieldValues["gk"];
                        float inte1=Form9->Query6->FieldValues["inte"];
                        float ak1=Form9->Query6->FieldValues["aki"];
                        float e1= Form9->Query6->FieldValues["Ek"]*1.23985e-4;
                        float yyy=1.0;

                        if (OKBottomDlg->CheckBox2->Checked==true && OKBottomDlg->RadioButton2->Checked==true)
                                {
                                for (int k=0; k < Form10->Series1->Count(); k++)
                                        {
                                        if (wave < Form10->Series1->XValues->Value[k])
                                                {
                                                yyy=Form10->Series1->YValues->Value[k]+
                                                (Form10->Series1->YValues->Value[k-1]-Form10->Series1->YValues->Value[k])/
                                                (Form10->Series1->XValues->Value[k-1]-Form10->Series1->XValues->Value[k])*
                                                (wave-Form10->Series1->XValues->Value[k]);
                                                break;
                                                }
                                        }
                                }
                        else
                                {
                                yyy=1.0;
                                }


                          sac=0;
                           for (int z=1; z < Form23->StringGrid1->RowCount;z++)
                             {
								if (fabs(atof(AnsiString(Form23->StringGrid1->Cells[2][z]).c_str())-asswave)<0.04)
                                {
								 sac=atof(AnsiString(Form23->StringGrid1->Cells[3][z]).c_str());
                                 break;
                                }
                                }
                              if (sac==0) sac=1;

                       inte1/=(yyy*sac);

                         ratio=log(inte1/gk1/ak1);
                             ekk=e1;
                             MySeries->AddXY(ekk,ratio);
                           Form9->Query6->Next();

                          }
                         }
                         if (lin2 !=0)
                         {
                         Form9->Query3->First();
                         for (int j=0; j <=lin2;j++)
                            {
                        float wave=Form9->Query3->FieldValues["wavelen"];
                        float asswave=Form9->Query3->FieldValues["asswavelen"];
                        float inte2=Form9->Query3->FieldValues["inte"];
                        float gi2=Form9->Query3->FieldValues["gi"];
                        float gk2=Form9->Query3->FieldValues["gk"];
                        float ak2=Form9->Query3->FieldValues["aki"];
                        float e2= Form9->Query3->FieldValues["Ek"]*1.23985e-4;
                        float yyy;

                        if (OKBottomDlg->CheckBox2->Checked==true && OKBottomDlg->RadioButton2->Checked==true)
                                {
                                for (int k=0; k < Form10->Series1->Count(); k++)
                                        {
                                        if (wave < Form10->Series1->XValues->Value[k])
                                                {
                                                yyy=Form10->Series1->YValues->Value[k]+
                                                (Form10->Series1->YValues->Value[k-1]-Form10->Series1->YValues->Value[k])/
                                                (Form10->Series1->XValues->Value[k-1]-Form10->Series1->XValues->Value[k])*
                                                (wave-Form10->Series1->XValues->Value[k]);
                                                break;
                                                }
                                        }
                                }
                        else
                                {
                                yyy=1.0;
                                }

                           sac=0;
                           for (int z=1; z < Form23->StringGrid1->RowCount;z++)
                             {
								 if (fabs(atof(AnsiString(Form23->StringGrid1->Cells[2][z]).c_str())-asswave)<0.04)
                                {
								 sac=atof(AnsiString(Form23->StringGrid1->Cells[3][z]).c_str());
                                 break;
                                }
                                }
                              if (sac==0) sac=1;

                        inte2/=(yyy*sac);

						float de=atof(AnsiString(Form27->Edit8->Text).c_str());
                        float tem=atof(AnsiString(Form27->Edit7->Text).c_str());

                             float ratio=log(inte2/gk2/ak2)-log(6.04e21/de*pow(tem,1.5));
                             float ekk=eion+e2;
                             MySeries->AddXY(ekk,ratio);
                             Form9->Query3->Next();
                            }

                        int kti=1;

                   }
                Form9->Query2->Next();
                }
              }

          // Form27->Show();

        }
//---------------------------------------------------------------------------

void __fastcall TForm6::FormClose(TObject *Sender, TCloseAction &Action)
{
SDIAppForm->OpenDialog->InitialDir=SDIAppForm->Edit14->Text;        
}
//---------------------------------------------------------------------------





void __fastcall TForm6::Button5Click(TObject *Sender)
{
char stringa[80]="This will clear the fit results in current template. Continue?";
if (MessageDlg(stringa, mtConfirmation, TMsgDlgButtons() << mbYes << mbNo << mbCancel, 0) != IDYES) return;
/*  AnsiString fn=ExtractFilePath(Application->ExeName)+"\Templates\\template.db";
 Form6->Table1->Active=true;
	Form6->Table1->Edit();

 for (int q=1; q < Form6->Table1->RecordCount+1; q++) {
 Form6->Table1->RecNo=q;
   Form6->Table1->FieldValues["fitwavelen"]=0.;
 }

Form6->Caption="Template";
SDIAppForm->OpenDialog->InitialDir=SDIAppForm->Edit14->Text;
*/
Form6->Table1->Active=true;
SDIAppForm->Series4->Active=true;
Form6->Table1->RecNo=1;

 for (int q=1; q < Form6->Table1->RecordCount+1; q++) {
 Form6->Table1->RecNo=q;
Form6->Table1->Edit();
Form6->Table1->FieldValues["fitwavelen"]=0.0;
Form6->Table1->FieldValues["inte"]=0.0;
Form6->Table1->FieldValues["wg"]=0.0;
Form6->Table1->FieldValues["wl"]=0.0;
 }
Form6->Caption="Template";
SDIAppForm->OpenDialog->InitialDir=SDIAppForm->Edit14->Text;
}
//---------------------------------------------------------------------------


