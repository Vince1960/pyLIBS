//---------------------------------------------------------------------------
#include <stdio.h>
#include <stdlib.h>
#include <vcl.h>
#include <fcntl.h>
#include <vector.h>
#include <fstream.h>
#pragma hdrstop
#include "SDIMain.h"
#include "Unit1.h"
#include "Unit5.h"
#include "Unit6.h"
#include "Unit9.h"
#include "Unit10.h"
#include "Unit20.h"
#include "Unit21.h"
#include "Unit22.h"
#include "Unit23.h"
#include "Unit27.h"
#include "Unit31.h"
static double glwlor,glaa,glww,gltstar;
#include <math.h>
#define COLORE 12632150
//---------------------------------------------------------------------------
#pragma package(smart_init)
#pragma resource "*.dfm"
TForm9 *Form9;
//---------------------------------------------------------------------------
__fastcall TForm9::TForm9(TComponent* Owner)
        : TForm(Owner)
{
}
//---------------------------------------------------------------------------


void __fastcall TForm9::Chart1ClickSeries(TCustomChart *Sender,
      TChartSeries *Series, int ValueIndex, TMouseButton Button,
      TShiftState Shift, int X, int Y)
{


if (atoi(AnsiString(Form9->LegendaAki->Text).c_str())==0)
        {
        Form9->LegendaAki->Text="1";
        Chart1->Canvas->Brush->Color=clWhite;
        Chart1->Canvas->Rectangle(Chart1->Left+2,Chart1->Top + Chart1->Height-133,Chart1->Left+110,Chart1->Top + Chart1->Height-5);
        Chart1->Canvas->Brush->Color=clBtnFace;
        Chart1->Canvas->Rectangle(Chart1->Left+5,Chart1->Top + Chart1->Height-110,Chart1->Left+50,Chart1->Top + Chart1->Height-98);
        Chart1->Canvas->Brush->Color=clGreen;
        Chart1->Canvas->Rectangle(Chart1->Left+5,Chart1->Top + Chart1->Height-95,Chart1->Left+50,Chart1->Top + Chart1->Height-83);
        Chart1->Canvas->Brush->Color=clLime;
        Chart1->Canvas->Rectangle(Chart1->Left+5,Chart1->Top + Chart1->Height-80,Chart1->Left+50,Chart1->Top + Chart1->Height-68);
        Chart1->Canvas->Brush->Color=clYellow;
        Chart1->Canvas->Rectangle(Chart1->Left+5,Chart1->Top + Chart1->Height-65,Chart1->Left+50,Chart1->Top + Chart1->Height-53);
        Chart1->Canvas->Brush->Color=clFuchsia;
        Chart1->Canvas->Rectangle(Chart1->Left+5,Chart1->Top + Chart1->Height-50,Chart1->Left+50,Chart1->Top + Chart1->Height-38);
        Chart1->Canvas->Brush->Color=clRed;
        Chart1->Canvas->Rectangle(Chart1->Left+5,Chart1->Top + Chart1->Height-35,Chart1->Left+50,Chart1->Top + Chart1->Height-23);
        Chart1->Canvas->Brush->Color=clMaroon;
        Chart1->Canvas->Rectangle(Chart1->Left+5,Chart1->Top + Chart1->Height-20,Chart1->Left+50,Chart1->Top + Chart1->Height-8);


        Chart1->Canvas->Brush->Color=clWhite;
        Chart1->Canvas->Font->Size=10;
        Chart1->Canvas->TextOutA(Chart1->Left+10, Chart1->Top + Chart1->Height-130, "Aki uncertainty");
        Chart1->Canvas->Font->Size=8;
        Chart1->Canvas->TextOutA(Chart1->Left+55, Chart1->Top + Chart1->Height-111, "not known");
        Chart1->Canvas->TextOutA(Chart1->Left+65, Chart1->Top + Chart1->Height-96, "< 10%");
        Chart1->Canvas->TextOutA(Chart1->Left+65, Chart1->Top + Chart1->Height-81, "< 18%");
        Chart1->Canvas->TextOutA(Chart1->Left+65, Chart1->Top + Chart1->Height-66, "< 25%");
        Chart1->Canvas->TextOutA(Chart1->Left+65, Chart1->Top + Chart1->Height-51, "< 40%");
        Chart1->Canvas->TextOutA(Chart1->Left+65, Chart1->Top + Chart1->Height-36, "< 50%");
        Chart1->Canvas->TextOutA(Chart1->Left+65, Chart1->Top + Chart1->Height-21, "> 50%");
        }

float soglia=atof(AnsiString(OKBottomDlg->Edit17->Text).c_str());
char sqls[300];
AnsiString ppp="Fit";
int lg;
if (Series->Name.SubString(1,3)!=ppp)
        {
        Series->XValues->Order=loNone;
        AnsiString ppp=Series->Name;
        AnsiString spe,io;
        int lg=StrLen(ppp.c_str());
        AnsiString sp=ppp.SubString(lg-1,2);
        if (sp != "II")
                {
                spe=ppp.SubString(1,lg-1);
                io=AnsiString("1");
                }
        else if ((sp=="II") & (lg==2))
                {
                spe="I";
                io=AnsiString("1");
                }
        else
                {
                spe=ppp.SubString(1,lg-2);
                io=AnsiString("2");
                }

		sprintf(sqls,"SELECT * FROM '%s' WHERE specie='%s' AND ion=%s AND aki!=0.0 AND aki !=-1.0 AND inte > 0.0",AnsiString(ExtractFileName(Form6->Table1->TableName)).c_str(),spe,io);

        Query3->SQL->Clear();
        Query3->SQL->Add(sqls);
        Query3->Open();
        Query3->First();
        Query3->MoveBy(ValueIndex);

        float wave=Query3->FieldValues["wavelen"];
        int acc=Query3->FieldValues["acc"];
        float ekk=Series->XValues->Value[ValueIndex];
        float yy=Series->YValues->Value[ValueIndex];
        float yyy;

        if (!Shift.Contains(ssShift))
        {
                /*primo caso, si fa vedere la riga*/
                if (Button==mbRight){
                                        char leg[32];
                                        if (atoi(io.c_str()) == 1)
                                        {
                                        sprintf(leg,"%s I %4.2f",spe,wave);
                                        }
                                        else
                                        {
                                        sprintf(leg,"%s II %4.2f",spe,wave);
                                        }
                                        switch (acc)
                                                {
                                                case 0:
                                                Chart1->Canvas->Brush->Color=clBtnFace;
                                                break;
                                                case 1: Chart1->Canvas->Brush->Color=clGreen;
                                                break;
                                                case 2: Chart1->Canvas->Brush->Color=clLime;
                                                break;
                                                case 3: Chart1->Canvas->Brush->Color=clYellow;
                                                break;
                                                case 4: Chart1->Canvas->Brush->Color=clFuchsia;
                                                break;
                                                case 5: Chart1->Canvas->Brush->Color=clRed;
                                                break;
                                                case 6: Chart1->Canvas->Brush->Color=clMaroon;
                                                }

                                        Chart1->Canvas->Rectangle(X+2,Y-16,X+72,Y+1);
                                        Chart1->Canvas->TextOutA(X+5, Y-14, leg);
                                        }

                else
                {

                /*secondo caso, si fa vedere la riga sulla curva di efficienza*/
                if ((OKBottomDlg->CheckBox2->Checked==true) & (OKBottomDlg->RadioButton2->Checked==true))
                {
                for (int k=0; k < Form10->Series1->Count(); k++)
                        {
                        if (Form10->Series1->XValues->Value[k] > wave)
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

                char leg[32];
                if (atoi(io.c_str()) == 1)
                {
                sprintf(leg,"%s I - %4.2f",spe,wave);
                }
                else
                {
                sprintf(leg,"%s II - %4.2f",spe,wave);
                }

        Form10->Series2->AddXY(wave,yyy,leg,Series->SeriesColor);

        SDIAppForm->Chart1->BottomAxis->Automatic=false;

		float rang=atof(AnsiString(OKBottomDlg->Edit9->Text).c_str());
        SDIAppForm->Chart1->BottomAxis->Automatic=false;
        SDIAppForm->Series4->XValues->Order = loAscending;
        SDIAppForm->Chart1->BottomAxis->SetMinMax(wave-rang, wave+rang);
        int fv=(SDIAppForm->Series4->FirstValueIndex+SDIAppForm->Series4->LastValueIndex)/2;
		rang=20*(atof(AnsiString(OKBottomDlg->Edit14->Text).c_str())+atof(AnsiString(OKBottomDlg->Edit15->Text).c_str()));
        SDIAppForm->Chart1->BottomAxis->SetMinMax(wave-rang, wave+rang);
        SDIAppForm->Chart1->LeftAxis->Automatic=true;
        Form6->Show();
        Form10->Show();
        }}
        else
        {

        /*secondo caso, si cambia l'Aki*/
        TLocateOptions Opts;
        Opts.Clear();
        Opts << loPartialKey << loCaseInsensitive;

        if (Form6->Table1->Locate("wavelen",wave,Opts))
        {goto bbb;}
        else
        {

        Form6->Table1->First();
                while (Form6->Table1->FieldValues["wavelen"]<wave)
                        {
                        Form6->Table1->Next();
                        }
                        float waves= Form6->Table1->FieldValues["wavelen"];
                        Form6->Table1->Prior();
                        float wavei=  Form6->Table1->FieldValues["wavelen"];
                        if (abs(wavei-wave) > (waves-wave)) {Form6->Table1->Next();}
        }




        bbb:

                if (Button==mbRight && Shift.Contains(ssShift))
                        {
                        if (Form6->Table1->FieldByName("Aki")->AsFloat > 0)
                                {
                                Series->ValueColor[ValueIndex]=COLORE;
                                int fv=Form6->Table1->RecNo;
                                SDIAppForm->Series4->ValueColor[fv-1]=COLORE;
                                Form6->Table1->Edit();
                                Form6->Table1->FieldValues["Aki"]=Form6->Table1->FieldValues["Aki"]*(-1);
                                Form6->Table1->Post();
                                return;
                                }
                        }
                else if (Button==mbLeft && Shift.Contains(ssShift))
                        {
                        if (Form6->Table1->FieldByName("Aki")->AsFloat < 0)
                                {
                                int fv=Form6->Table1->RecNo;
                                SDIAppForm->Series4->ValueColor[fv-1]=clYellow;
                                Series->ValueColor[ValueIndex]=clTeeColor;
                                Form6->Table1->Edit();
                                Form6->Table1->FieldValues["Aki"]=Form6->Table1->FieldValues["Aki"]*(-1);
                                Form6->Table1->Post();
                                return;
                                }
                        }

              }

        }
}

//---------------------------------------------------------------------------

void __fastcall TForm9::StringGrid1SelectCell(TObject *Sender, int ACol,
      int ARow, bool &CanSelect)
{
char snam[300];
if (StringGrid1->Cells[1][ARow]!="")
        {
        if (StringGrid1->Cells[0][ARow]=="X")
                {
                StringGrid1->Cells[0][ARow]="";
                Chart1->Series[ARow-1]->Active=true;

                sprintf(snam,"Fit%s",Chart1->Series[ARow-1]->Name);

                for (int i=0;i < Chart1->SeriesCount();i++)
                        {
                        if (Chart1->Series[i]->Name==snam)
                                {
                                Chart1->Series[i]->Active=true;
                                break;
                                }
                        }
                }
        else
                {
                StringGrid1->Cells[0][ARow]="X";
                Chart1->Series[ARow-1]->Active=false;
                sprintf(snam,"Fit%s",Chart1->Series[ARow-1]->Name);

                for (int i=0;i < Chart1->SeriesCount();i++)
                        {
                        if (Chart1->Series[i]->Name==snam)
                                {
                                Chart1->Series[i]->Active=false;
                                break;
                                }
                        }
                }
        }
}
//---------------------------------------------------------------------------

void __fastcall TForm9::Button3Click(TObject *Sender)
{
Form9->Query1->Active=false;
Form9->Query1->DatabaseName=ExtractFilePath(Form6->Table1->TableName);
Form9->Query1->Active=true;
float soglia=atof(AnsiString(OKBottomDlg->Edit17->Text).c_str());
char sqls[300];
sprintf(sqls,"SELECT DISTINCT specie,ion FROM %s WHERE aki > %f AND inte > 0.0 ORDER BY specie,ion",AnsiString(ExtractFileName(Form6->Table1->TableName)).c_str(),soglia);
Query1->SQL->Clear();
Query1->SQL->Add(sqls);
Query1->Open();
Query1->First();
AnsiString tt;
tt=AnsiString("Deselect All");
if (Trim(Button3->Caption) == tt)
        {
        Button3->Caption = AnsiString("Select All");
        for (int i=1; i <= Query1->RecordCount; i++)
                {
                StringGrid1->Cells[0][i]="X";
                }
        for (int i=0; i<Chart1->SeriesCount(); i++)
                {
                Chart1->Series[i]->Active=false;
                }
        }
else
        {
        Button3->Caption = AnsiString("Deselect All");
        for (int i=1; i <= Query1->RecordCount;i++)
                {
                StringGrid1->Cells[0][i]="";
                }
        for (int i=0; i<Chart1->SeriesCount(); i++)
                {
                Chart1->Series[i]->Active=true;
                }
        }
}
//---------------------------------------------------------------------------

void __fastcall TForm9::Button2Click(TObject *Sender)
{
void report (AnsiString nomereport, AnsiString nomefile, AnsiString nometempl);
double zZ(AnsiString spp,int ion,float ti);
Form9->SaveDialog1->Title="Save Report";
Form9->SaveDialog1->Filter="Report|*.REP";
Form9->SaveDialog1->FileName = "*.REP";
Form9->SaveDialog1->InitialDir="C:\\LIBS++\\Reports";
char stringa[80]="The file already exists. Overwrite?";
if (Form9->SaveDialog1->Execute())
	{
		if (FileExists(Form9->SaveDialog1->FileName))
		{
			if (MessageDlg(stringa, mtConfirmation, TMsgDlgButtons() << mbYes << mbNo <<
				mbCancel, 0) != IDYES)
				return;
		}

  FILE *out;

   out = fopen(AnsiString(Form9->SaveDialog1->FileName).c_str(), "w");
double zZ(AnsiString spp,int ion,float ti);
void fit(float x[], float y[], int ndata, float sig[], int mwt, float *a, float *b, float *siga, float *sigb, float *chi2, float *q);
float rtbis(double (*func)(double), double x1, double x2, float xacc);
double test(double x);
int colo[34]={clRed,clGreen,clBlue,clPurple,clGray,clMaroon,clNavy,clOlive,clLtGray,clFuchsia,clWhite,clTeal,clSilver,clLime,clAqua,clBlack+200,clRed+200,clGray+200,clAqua+200,clBlue+200,clGreen+200,clBlack+200,clMaroon+200,clNavy+200,clDkGray+200,clOlive+200,clPurple+200,clLtGray+200,clFuchsia+200,clWhite+200,clTeal+200,clSilver+200,clLime+200};
float soglia=atof(AnsiString(OKBottomDlg->Edit17->Text).c_str());


// Inizio plot
Form9->Query1->Active=false;
Form9->Query1->DatabaseName=ExtractFilePath(Form6->Table1->TableName);
Form9->Query2->Active=false;
Form9->Query2->DatabaseName=ExtractFilePath(Form6->Table1->TableName);
Form9->Query3->Active=false;
Form9->Query3->DatabaseName=ExtractFilePath(Form6->Table1->TableName);
Form9->Query6->Active=false;
Form9->Query6->DatabaseName=ExtractFilePath(Form6->Table1->TableName);
Form9->Query1->Active=true;
Form9->Query2->Active=true;
Form9->Query3->Active=true;
Form9->Query6->Active=true;


double xs,ys,yqs,xqs,xy,errore,delta,kt,q,us,eq;

char sqls[300];
int progre=0;
sprintf(sqls,"SELECT DISTINCT specie,ion FROM %s WHERE aki !=0.0 AND aki != -1.0 AND inte > 0.0 ORDER BY specie,ion",AnsiString(ExtractFileName(Form6->Table1->TableName)).c_str());
Form9->Query1->SQL->Clear();
Form9->Query1->SQL->Add(sqls);
Form9->Query1->Open();
Form9->Query1->First();
sprintf(sqls,"SELECT DISTINCT specie FROM %s WHERE aki !=0.0 AND aki != -1.0 AND inte > 0.0 ORDER BY specie",AnsiString(ExtractFileName(Form6->Table1->TableName)).c_str());
Form9->Query2->SQL->Clear();
Form9->Query2->SQL->Add(sqls);
Form9->Query2->Open();
Form9->Query2->First();


char sname[32];
for (int i=0; i < Form9->Query1->RecordCount; i++)
		{

		Form9->Edit3->Text=Form9->Query1->FieldValues["specie"];

        Form9->Edit4->Text=Form9->Query1->FieldValues["ion"];

		int ioniz=Form9->Query1->FieldValues["ion"];
		switch(ioniz)
				{
				case 1:
				sprintf(sname,"%sI",AnsiString(Trim(Form9->Edit3->Text)).c_str());
				break;
				case 2:
				sprintf(sname,"%sII",AnsiString(Trim(Form9->Edit3->Text)).c_str());
                break;
				}

		sprintf(sqls,"SELECT * FROM %s WHERE specie='%s' AND ion=%s AND aki !=0.0 AND aki != -1.0 AND inte > 0.0",AnsiString(ExtractFileName(Form6->Table1->TableName)).c_str(),AnsiString(Form9->Edit3->Text).c_str(),Form9->Edit4->Text);
		Form9->Query3->SQL->Clear();
		Form9->Query3->SQL->Add(sqls);
		Form9->Query3->Open();
        Form9->Query3->First();

		float yyy;
		float z;
        int reco= Form9->Query3->RecordCount;

        for (int j=0; j < reco; j++)
				{
                progre++;
                float wave=Form9->Query3->FieldValues["wavelen"];
                float inte=Form9->Query3->FieldValues["inte"];
                float erro= Form9->Query3->FieldValues["error-inte"];
                float aki= Form9->Query3->FieldValues["aki"];
                int gk= Form9->Query3->FieldValues["gk"];
				float Ek= Form9->Query3->FieldValues["Ek"]*1.23985e-4;

			  float kappati=atof(AnsiString(Form9->Edit13->Text).c_str());

				z=zZ(AnsiString(Trim(Form9->Edit3->Text)).c_str(),ioniz,kappati);

                if ((OKBottomDlg->CheckBox2->Checked==true) & (OKBottomDlg->RadioButton2->Checked==true))
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
                float sac;
                aaa:
				if (atof(AnsiString(Form23->StringGrid1->Cells[3][progre]).c_str())!=0)
                        {
						sac=atof(AnsiString(Form23->StringGrid1->Cells[3][progre]).c_str());
                        }
                else
						{
                        sac=1.0;
						}

   fprintf(out,"%s %4.2f %4.2f %4.2f %4.2f %i %4.2f %4.2f\n",sname,wave,inte,aki,Ek,gk,z,yyy);



                inte/=(yyy*sac);
				erro/=(yyy*sac);

				float yy=log(inte/fabs(aki*gk));

	 Form9->Query3->Next();
                }

		Form9->Query1->Next();
				}


	for (int J = 1; J < Form9->StringGrid2->RowCount; J++)
  {
  if (AnsiString(Form9->StringGrid2->Cells[1][J]).c_str() != "") {

    fprintf(out,"%s %s %s %s %s\n",AnsiString(Form9->StringGrid2->Cells[1][J]).c_str(),AnsiString(Form9->StringGrid2->Cells[2][J]).c_str(),AnsiString(Form9->StringGrid2->Cells[3][J]).c_str(),AnsiString(Form9->StringGrid2->Cells[4][J]).c_str(),AnsiString(Form9->StringGrid2->Cells[5][J]).c_str());
  }

   }
						fclose(out);
		}

	}
//---------------------------------------------------------------------------



void __fastcall TForm9::Copy1Click(TObject *Sender)
{
Graphics::TBitmap *FormImage;
TClipboard *MyClip;

MyClip = new TClipboard();

FormImage = GetFormImage();
MyClip->Assign(FormImage);
}
//---------------------------------------------------------------------------

void __fastcall TForm9::Button1Click(TObject *Sender)
{
void calcola();
for (int w=1; w<=Form20->StringGrid1->RowCount;w++)
{
Form20->StringGrid1->Cells[1][w]="";
Form20->StringGrid1->Cells[2][w]="";
Form20->StringGrid1->Cells[3][w]="";
Form20->StringGrid1->Cells[4][w]="";
Form20->StringGrid1->Cells[5][w]="";
Form20->StringGrid1->Cells[6][w]="";
}
calcola();
}
//---------------------------------------------------------------------------


void __fastcall TForm9::ComboBox1Change(TObject *Sender)
{
 RadioGroup1->ItemIndex=3;
}
//---------------------------------------------------------------------------

void __fastcall TForm9::ComboBox2Change(TObject *Sender)
{
RadioGroup2->ItemIndex=3;
}
//---------------------------------------------------------------------------

void __fastcall TForm9::SaveData1Click(TObject *Sender)
{
Form9->SaveDialog1->Title="Save Data";
Form9->SaveDialog1->Filter="Data|*.BLZ";
Form9->SaveDialog1->FileName = "*.BLZ";
Form9->SaveDialog1->InitialDir=ExtractFilePath(Application->ExeName)+"Reports";
char stringa[80]="The file already exists. Overwrite?";
if (Form9->SaveDialog1->Execute())
		{
		if (FileExists(Form9->SaveDialog1->FileName))
				{
                if (MessageDlg(stringa, mtConfirmation, TMsgDlgButtons() << mbYes << mbNo <<
 			mbCancel, 0) != IDYES)
          	return;
        }

FILE *out;
out = fopen(AnsiString(Form9->SaveDialog1->FileName).c_str(), "w");
Form9->Query1->First();
Form9->Query2->First();
int sc= Form9->Chart1->SeriesCount();
float waveline;
float akkappai;

for (int i=0; i < sc; i++)
        {
        char sqls[300];
        AnsiString ppp=Form9->Chart1->Series[i]->Name;
        AnsiString spe,io;
        int lg=StrLen(ppp.c_str());
        AnsiString sp=ppp.SubString(lg-1,2);
        if (sp != "II")
                {
                spe=ppp.SubString(1,lg-1);
                io=AnsiString("1");
                }
        else if ((sp=="II") & (lg==2))
                {
                spe="I";
                io=AnsiString("1");
                }
        else
                {
                spe=ppp.SubString(1,lg-2);
                io=AnsiString("2");
                }
		float soglia=atof(AnsiString(OKBottomDlg->Edit17->Text).c_str());
		sprintf(sqls,"SELECT * FROM %s WHERE specie='%s' AND ion=%s AND aki !=0.0 AND aki != -1.0 AND inte > 0.0",AnsiString(ExtractFileName(Form6->Table1->TableName)).c_str(),spe,io,soglia);
        Form9->Query3->SQL->Clear();
        Form9->Query3->SQL->Add(sqls);
        Form9->Query3->Open();
        Form9->Query3->First();

        int reco= Form9->Query3->RecordCount;

        for (int j=0;j < reco;j++)
                {
                waveline=Form9->Query3->FieldValues["wavelen"];
                akkappai=Form9->Query3->FieldValues["aki"];

                if (akkappai > soglia)
						{
						fprintf(out,"%s %4.2f %4.2f %4.2f \n",ppp.c_str(),Form9->Chart1->Series[i]->XValues->Value[j],Form9->Chart1->Series[i]->YValues->Value[j],waveline);
                        }
                Form9->Query3->Next();
                }
        }

fclose(out);
}
SDIAppForm->OpenDialog->InitialDir=SDIAppForm->Edit14->Text;
}
//---------------------------------------------------------------------------

void __fastcall TForm9::Edit8Change(TObject *Sender)
{
  double zZ(AnsiString spp,int i,float ti);
if (Form9->Edit8->Text !="")
        {
        // Calcolo concentrazioni a meno di F
        Form9->Query2->First();
 //      ShowMessage("entro in form9");
        for (int i=0; i < Form9->Query2->RecordCount; i++)
                {
				if (atof(AnsiString(Form9->StringGrid2->Cells[2][i+1]).c_str())==0)
                        {
                        AnsiString spp=Form9->StringGrid2->Cells[1][i+1];



                        char sp1[10],sp2[10],sqls[300];
						sprintf(sp1,"%sI",AnsiString(Trim(spp)).c_str());
						sprintf(sp2,"%sII",AnsiString(Trim(spp)).c_str());

                        float eion;
                        sprintf(sqls,"SELECT * FROM elementi WHERE [specie]='%s'",spp);

						Form9->Query5->SQL->Clear();
                        Form9->Query5->SQL->Add(sqls);
                        Form9->Query5->Open();
                        eion=Form9->Query5->FieldValues["en_ion"]*0.000123985;
						Form9->Query1->First();
						for (int j=0; j< Form9->Query1->RecordCount; j++)
                                {
                                // se c'e' la specie neutra ma non la ionizzata

								if (Form9->StringGrid1->Cells[1][j+1]==sp1 && atof(AnsiString(Form9->StringGrid1->Cells[4][j+1]).c_str()) !=0.0)
                                        {
										//ShowMessage(sp1);
										//ShowMessage(j);
										float ne=atof(AnsiString(Form9->StringGrid2->Cells[4][i+1]).c_str());
										float ti=atof(AnsiString(Form9->StringGrid1->Cells[3][j+1]).c_str());
										float pop1=atof(AnsiString(Form9->StringGrid1->Cells[4][j+1]).c_str());
										float z1=atof(AnsiString(Form9->StringGrid1->Cells[5][j+1]).c_str());

										if (Form9->CheckBox1->Checked == true && atof(AnsiString(Form9->Edit11->Text).c_str()) !=0.0)
												{
												ti=atof(AnsiString(Form9->Edit11->Text).c_str());
                                                for (int w=1;w<Form22->StringGrid1->RowCount;w++)
                                                        {
                                                        if (Form22->StringGrid1->Cells[1][w]==Trim(spp))
                                                                {
																ti=atof(AnsiString(Form22->StringGrid1->Cells[2][w]).c_str());
                                                                break;
                                                                }
                                                        }
                                                }



   //calcolo funzione di partizione per specie ionizzata con Payling
		double z2=zZ(spp,2,ti);
		  // fine calcolo partizione ionizzata
										double conc=exp(pop1)*z1*(1.0+(6.04e+21/ne*pow((double)ti,1.5)*z2/z1*exp(-eion/ti)));
										double ratio=exp(pop1)*z1/conc;
										char tmd[20];
										sprintf(tmd,"%1.4f",ratio);
										Form9->StringGrid2->Cells[5][i+1]=tmd;
										char cm[10];
										sprintf(cm,"%1.4f",conc);
										Form9->StringGrid2->Cells[2][i+1]=cm;
										sprintf(sqls,"SELECT * FROM elementi WHERE [specie]='%s'",spp);
                                        Form9->Query5->SQL->Clear();
                                        Form9->Query5->SQL->Add(sqls);
                                        Form9->Query5->Open();
                                        float massa=Form9->Query5->FieldValues["m_atomica"];
                                        float cmassa=massa*conc;
                                        sprintf(cm,"%1.4f",cmassa);
                                        Form9->StringGrid2->Cells[3][i+1]=cm;
                                        break;
                                        }

                                        // se c'e' lo ionizzato ma non il neutro

								else if (Form9->StringGrid1->Cells[1][j+1]==sp2 && atof(AnsiString(Form9->StringGrid1->Cells[4][j+1]).c_str()) !=0.0)
                                        {
										//ShowMessage(sp2);
										//ShowMessage(j);
										float ne=atof(AnsiString(Form9->StringGrid2->Cells[4][i+1]).c_str());
										float ti=atof(AnsiString(Form9->StringGrid1->Cells[3][j+1]).c_str());
										float pop2=atof(AnsiString(Form9->StringGrid1->Cells[4][j+1]).c_str());
										float z2=atof(AnsiString(Form9->StringGrid1->Cells[5][j+1]).c_str());

										if (Form9->CheckBox1->Checked == true && atof(AnsiString(Form9->Edit11->Text).c_str()) !=0.0)
                                                {
												ti=atof(AnsiString(Form9->Edit11->Text).c_str());
                                                for (int w=1;w<Form22->StringGrid1->RowCount;w++)
                                                        {
                                                        if (Form22->StringGrid1->Cells[1][w]==Trim(spp))
                                                                {
																ti=atof(AnsiString(Form22->StringGrid1->Cells[2][w]).c_str());
                                                                break;
                                                                }
                                                        }
                                                }



   //calcolo funzione di partizione per specie neutra con Payling

   double z1=zZ(spp,1,ti);
										//fine calcolo partizione neutra

										double conc=exp(pop2)*z2*(1.0+(ne/6.04e+21*pow((double)ti,-1.5)*z1/z2*exp(eion/ti)));
										double ratio=1.0-exp(pop2)*z2/conc;
										char tmd[20];
										sprintf(tmd,"%1.4f",ratio);
										Form9->StringGrid2->Cells[5][i+1]=tmd;

										char cm[10];
										sprintf(cm,"%1.4f",conc);
                                        Form9->StringGrid2->Cells[2][i+1]=cm;
                                        sprintf(sqls,"SELECT * FROM elementi WHERE [specie]='%s'",spp);
                                        Form9->Query5->SQL->Clear();
                                        Form9->Query5->SQL->Add(sqls);
                                        Form9->Query5->Open();
                                        float massa=Form9->Query5->FieldValues["m_atomica"];
                                        float cmassa=massa*conc;
                                        sprintf(cm,"%1.4f",cmassa);
                                        Form9->StringGrid2->Cells[3][i+1]=cm;
                                        break;
                                        }

                                Form9->Query1->Next();
                                }

                        //inserire else qui
						if (atof(AnsiString(Form9->StringGrid2->Cells[2][i+1]).c_str())==0.0)
                               {
                                ShowMessage(AnsiString("Warning: there are no more available lines from ") + Form9->StringGrid2->Cells[1][i+1].c_str());
                                double conc=0.0;
                                char cm[10];
                                sprintf(cm,"%1.4f",conc);
                                Form9->StringGrid2->Cells[2][i+1]=cm;
                                Form9->StringGrid2->Cells[3][i+1]=cm;
                                }
                        }
                Form9->Query2->Next();
                }

        // Normalizzazione
      //  ShowMessage("entro in normalizzazione");
        Form9->Query2->First();
        float totc=0.0;
        float totm=0.0;
        for (int i=0;i < Form9->Query2->RecordCount; i++)
                {
				totc+=atof(AnsiString(Form9->StringGrid2->Cells[2][i+1]).c_str());
				totm+=atof(AnsiString(Form9->StringGrid2->Cells[3][i+1]).c_str());
                Form9->Query2->Next();
                }

        //calcolo la densità del plasma
        float ration=0.0;     // rapporto neutro su totale
        float concf=0.0;      // densità numerica dell'elemento a meno di f
        float conca=0.0;      // densità numerica del plasma assoluta
        float densipla=0.0;   // somma delle densità di tutti gli ioni a meno di f
        float ffactor=-1.0;   // fattore f
        char sms[50];
        for (int i=0;i < Form9->Query2->RecordCount; i++)
                {
				concf=atof(AnsiString(Form9->StringGrid2->Cells[2][i+1]).c_str());
				ration=atof(AnsiString(Form9->StringGrid2->Cells[5][i+1]).c_str());
                densipla+=concf*(1-ration);
                //ShowMessage(i);
              //sprintf(sms, "per elemento %d gli ioni sono %e",i, concf*(1-ration));
            //ShowMessage(sms);
                Form9->Query2->Next();
                }

        sprintf(sms,"il numero totale di ioni osservati è %e",densipla);
   //     ShowMessage(sms);
        if (densipla != 0)
                {
				ffactor= (atof(AnsiString(Form9->Edit8->Text).c_str()))/densipla;
                conca=totc*ffactor;
                }
        else
                {
				conca=atof(AnsiString(Form9->Edit8->Text).c_str());
                }
        char dm1[10];
        char dm2[10];
        sprintf(dm1,"%1.2e",conca);
        sprintf(dm2,"%1.2e",ffactor);
        Form21->Edit3->Text=dm1;
        Form21->Edit4->Text=dm2;

        // Calcolo concentrazioni assolute
        Form9->Query2->First();
        char cm[10];
        Form21->Series1->Clear();
        for (int i=0;i < Form9->Query2->RecordCount; i++)
                {
				float cc=atof(AnsiString(Form9->StringGrid2->Cells[2][i+1]).c_str())/totc*100.;
                sprintf(cm,"%1.4f",cc);
                Form9->StringGrid2->Cells[2][i+1]=cm;
				float cms=atof(AnsiString(Form9->StringGrid2->Cells[3][i+1]).c_str())/totm*100.;
                sprintf(cm,"%1.4f",cms);
                Form9->StringGrid2->Cells[3][i+1]=cm;
                int slic=1.e4*cms;
                Form21->Series1->Add(slic,AnsiString(Form9->StringGrid2->Cells[1][i+1]).c_str(),clTeeColor);
                Form9->Query2->Next();
                }
        if(Form9->CheckBox3->Checked == true)
        {
        Form21->Show();
        }
        }
}
//---------------------------------------------------------------------------
  double zZ(AnsiString spp,int ion,float ti)
  {
  char sqls[300];
  float t1,t2,p1,p2;
  ti*= 11604.45;
  sprintf(sqls,"SELECT * FROM partfunctPay WHERE element='%s' and ion=%i and temperature <%f",spp,ion,ti);
  Form9->Query9->SQL->Clear();
 Form9->Query9->SQL->Add(sqls);
 Form9->Query9->Open();

 if (Form9->Query9->RecordCount >0)
  {
  Form9->Query9->Last();
  t1=Form9->Query9->FieldValues["temperature"];
   p1=Form9->Query9->FieldValues["partfunct"];
   }
   else
   {
      sprintf(sqls,"SELECT * FROM partfunctPay WHERE element='%s' and ion=%i",spp,ion);
 Form9->Query9->SQL->Clear();
 Form9->Query9->SQL->Add(sqls);
 Form9->Query9->Open();
     Form9->Query9->First();
  t1=Form9->Query9->FieldValues["temperature"];
   p1=Form9->Query9->FieldValues["partfunct"];
        Form9->Query9->Next();
  t2=Form9->Query9->FieldValues["temperature"];
   p2=Form9->Query9->FieldValues["partfunct"];
     return p1+(p2-p1)/(t2-t1)*(ti-t1);
   }
sprintf(sqls,"SELECT * FROM partfunctPay WHERE element='%s' and ion=%i and temperature >%f",spp,ion,ti);
  Form9->Query9->SQL->Clear();
 Form9->Query9->SQL->Add(sqls);
 Form9->Query9->Open();
 if (Form9->Query9->RecordCount >0)
  {
  Form9->Query9->First();
   t2=Form9->Query9->FieldValues["temperature"];
   p2=Form9->Query9->FieldValues["partfunct"];
   }
   else
   {
      sprintf(sqls,"SELECT * FROM partfunctPay WHERE element='%s' and ion=%i",spp,ion);
 Form9->Query9->SQL->Clear();
 Form9->Query9->SQL->Add(sqls);
 Form9->Query9->Open();
     Form9->Query9->Last();
  t2=Form9->Query9->FieldValues["temperature"];
   p2=Form9->Query9->FieldValues["partfunct"];
        Form9->Query9->MoveBy(-1);
  t1=Form9->Query9->FieldValues["temperature"];
   p1=Form9->Query9->FieldValues["partfunct"];
   }
  return p1+(p2-p1)/(t2-t1)*(ti-t1);
  }


void __fastcall TForm9::Button4Click(TObject *Sender)
{
Form6->Show();
}
//---------------------------------------------------------------------------

void __fastcall TForm9::Refresh1Click(TObject *Sender)
{
void showboltz();
Form9->LegendaAki->Text="0";
showboltz();
}
//---------------------------------------------------------------------------

void __fastcall TForm9::ChangeBackground1Click(TObject *Sender)
{
int colore;
     SDIAppForm->ColorDialog1->Color=Form9->Chart1->BackColor;
    if (SDIAppForm->ColorDialog1->Execute())
    colore = SDIAppForm->ColorDialog1->Color;
    Form9->Chart1->Color=colore;
    return;
}
//---------------------------------------------------------------------------

void __fastcall TForm9::GridXONOff1Click(TObject *Sender)
{
  if (Form9->Chart1->BottomAxis->Grid->Visible==false)  Form9->Chart1->BottomAxis->Grid->Visible=true;
   else
   Form9->Chart1->BottomAxis->Grid->Visible=false;
}
//---------------------------------------------------------------------------

void __fastcall TForm9::GridYOnOff1Click(TObject *Sender)
{
  if (Form9->Chart1->LeftAxis->Grid->Visible==false)  Form9->Chart1->LeftAxis->Grid->Visible=true;
   else
   Form9->Chart1->LeftAxis->Grid->Visible=false;
}
//---------------------------------------------------------------------------

void __fastcall TForm9::AnimatedZoomOnOff1Click(TObject *Sender)
{
 if (Form9->Chart1->AnimatedZoom==false) Form9->Chart1->AnimatedZoom=true;
   else
   Form9->Chart1->AnimatedZoom=false;
}
//---------------------------------------------------------------------------

void __fastcall TForm9::OPC1Click(TObject *Sender)
{
Form31->Show();
}
//---------------------------------------------------------------------------


